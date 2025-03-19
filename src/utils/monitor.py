"""
Monitor-Modul für die automatische Überwachung und Verwaltung von Verbrauchsdaten.
"""

import time
import logging
import schedule
import os
import sys
import threading
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from src.api.usability import ConsumptionAPI
from src.utils.logger import setup_logger
from src.utils.interval_calculator import calculate_next_check_interval

# Logger für dieses Modul konfigurieren
logger = setup_logger(
    name="data_monitor",
    level="INFO",
    log_to_file=True
)

class DataMonitor:
    """
    Überwacht den Datenverbrauch eines Vertrags und führt automatische Aktionen aus,
    wenn bestimmte Schwellenwerte erreicht werden.
    """
    
    def __init__(self, contract_id: str, username: str = None, password: str = None, guest_url: str = None,
                 threshold_gb: float = 1.0, check_interval_seconds: int = 60,
                 log_retention_hours: int = 12, fast_check_interval_seconds: int = 5,
                 max_check_interval_seconds: int = 300, dynamic_interval: bool = True,
                 initial_dynamic_interval_seconds: int = 60):
        """
        Initialisiert den DataMonitor.
        
        Args:
            contract_id: Die Vertrags-ID, die überwacht werden soll
            username: Benutzername für die Authentifizierung (optional)
            password: Passwort für die Authentifizierung (optional)
            guest_url: Gast-Link für den Zugriff ohne Anmeldedaten (optional)
            threshold_gb: Schwellenwert in GB, bei dem eine Aktion ausgelöst wird
            check_interval_seconds: Intervall in Sekunden, in dem die Daten überprüft werden
            log_retention_hours: Anzahl der Stunden, für die Logs aufbewahrt werden sollen
            fast_check_interval_seconds: Schnelleres Prüfintervall in Sekunden, wenn der Schwellenwert unterschritten wird
            max_check_interval_seconds: Maximales Prüfintervall in Sekunden (Standard: 300 = 5 Minuten)
            dynamic_interval: Ob das Prüfintervall dynamisch basierend auf der Verbrauchsrate berechnet werden soll
            initial_dynamic_interval_seconds: Initiales Intervall in Sekunden für die dynamische Berechnung (Standard: 60 = 1 Minute)
        """
        self.contract_id = contract_id
        self.username = username
        self.password = password
        self.guest_url = guest_url
        self.threshold_gb = threshold_gb
        self.check_interval_seconds = check_interval_seconds
        self.original_check_interval_seconds = check_interval_seconds  # Speichern des ursprünglichen Intervalls
        self.fast_check_interval_seconds = fast_check_interval_seconds  # Schnelleres Intervall
        self.max_check_interval_seconds = max_check_interval_seconds  # Maximales Intervall
        self.initial_dynamic_interval_seconds = initial_dynamic_interval_seconds  # Initiales Intervall für dynamische Berechnung
        self.log_retention_hours = log_retention_hours
        self.dynamic_interval = dynamic_interval  # Neue Option für dynamische Intervallberechnung
        self.api = ConsumptionAPI()
        self.below_threshold = False  # Flag, um zu verfolgen, ob wir unter dem Schwellenwert sind
        self.history_data = {}  # Verlaufsdaten für die Intervallberechnung
        self.first_dynamic_check = True  # Flag für den ersten dynamischen Check
        self.last_check_data = None  # Speichert die Daten des letzten Abrufs
        self.last_check_time = None  # Speichert die Zeit des letzten Abrufs
        self.interval_lock = threading.Lock()  # Mutex für die Intervallberechnung
        
        # Logger für diese Instanz konfigurieren - verwende den zentralen Logger
        self.logger = setup_logger(
            name=f"monitor_{contract_id}",
            level="INFO",
            log_to_file=True
        )
        
        # Authentifizierung einrichten
        if guest_url:
            # Verwende Gast-Link für die Authentifizierung
            self.api.set_session(guest_url=guest_url)
        elif username and password:
            # Verwende Benutzername und Passwort für die Authentifizierung
            self.api.set_session(username=username, password=password)
        
        self.running = False
    
    def check_data_usage(self) -> Dict[str, Any]:
        """
        Ruft die aktuellen Verbrauchsdaten ab und prüft, ob eine Aktion erforderlich ist.
        
        Returns:
            Ein Dictionary mit den Verbrauchsdaten und dem Ergebnis der Aktion
        """
        current_time = time.time()
        current_time_str = time.strftime("%H:%M:%S", time.localtime(current_time))
        self.logger.info(f"Überprüfe Datenverbrauch für Vertrag {self.contract_id} um {current_time_str}")
        
        try:
            # Verbrauchsdaten abrufen
            summary = self.api.get_consumption_summary(self.contract_id)
            
            if not summary or "datenvolumen" not in summary:
                self.logger.error("Keine gültigen Verbrauchsdaten erhalten")
                return {"erfolg": False, "nachricht": "Keine gültigen Verbrauchsdaten erhalten"}
            
            # Datenvolumen extrahieren
            data_volume = summary["datenvolumen"]
            verbraucht_gb = data_volume.get("verbraucht_gb", 0)
            highspeed_limit_gb = data_volume.get("highspeed_limit_gb", 0)
            remaining_gb = highspeed_limit_gb - verbraucht_gb
            kann_nachbuchen = data_volume.get("kann_nachbuchen", False)
            aktualisiert_timestamp = data_volume.get("aktualisiert_timestamp", current_time)
            aktualisiert_am = data_volume.get("aktualisiert_am", "Unbekannt")
            
            self.logger.info(f"Aktueller Datenverbrauch: {verbraucht_gb:.2f} GB von {highspeed_limit_gb:.2f} GB")
            self.logger.info(f"Verbleibendes Highspeed-Volumen: {remaining_gb:.2f} GB")
            self.logger.info(f"Daten aktualisiert am: {aktualisiert_am}")
            
            # Wenn wir bereits einen letzten Abruf haben, aktualisieren wir die Verlaufsdaten
            if self.last_check_data is not None and self.last_check_time is not None:
                # Extrahiere die Daten des letzten Abrufs
                letzte_datenvolumen = self.last_check_data.get("datenvolumen", {})
                letzte_verbraucht_gb = letzte_datenvolumen.get("verbraucht_gb", verbraucht_gb)
                letzte_aktualisiert_timestamp = letzte_datenvolumen.get("aktualisiert_timestamp", self.last_check_time)
                
                # Berechne die Zeit zwischen den Datenaktualisierungen (nicht zwischen den Abrufen)
                zeit_diff_sekunden = aktualisiert_timestamp - letzte_aktualisiert_timestamp
                
                # Aktualisiere die Verlaufsdaten für die Intervallberechnung
                with self.interval_lock:
                    self.history_data["letzte_messung"] = letzte_datenvolumen
                    self.history_data["letzte_messung_zeit"] = letzte_aktualisiert_timestamp
                
                # Logge die Messung
                verbrauch_diff_gb = verbraucht_gb - letzte_verbraucht_gb
                if zeit_diff_sekunden > 0 and verbrauch_diff_gb > 0:
                    verbrauchsrate_gb_pro_sekunde = verbrauch_diff_gb / zeit_diff_sekunden
                    verbrauchsrate_gb_pro_minute = verbrauchsrate_gb_pro_sekunde * 60
                    verbrauchsrate_mb_pro_minute = verbrauchsrate_gb_pro_minute * 1024
                    
                    self.logger.info(f"=== Messung seit letzter Datenaktualisierung ===")
                    self.logger.info(f"Zeit seit letzter Datenaktualisierung: {zeit_diff_sekunden:.1f} Sekunden")
                    self.logger.info(f"Verbrauch seit letzter Datenaktualisierung: {verbrauch_diff_gb*1024:.2f} MB")
                    self.logger.info(f"Aktuelle Verbrauchsrate: {verbrauchsrate_gb_pro_minute:.4f} GB/Minute ({verbrauchsrate_mb_pro_minute:.1f} MB/Minute)")
            
            # Speichere die aktuellen Daten für den nächsten Abruf
            self.last_check_data = summary
            self.last_check_time = current_time
            
            # Prüfen, ob der Schwellenwert unterschritten wurde oder eine Nachbuchung möglich ist
            below_threshold = remaining_gb < self.threshold_gb
            
            # Wenn dynamische Intervallberechnung aktiviert ist, berechne das nächste Intervall
            if self.dynamic_interval:
                with self.interval_lock:  # Lock für die Intervallberechnung verwenden
                    # Beim ersten Check verwenden wir das initiale Intervall
                    if self.first_dynamic_check:
                        self.first_dynamic_check = False
                        next_interval = self.initial_dynamic_interval_seconds
                        self.logger.info(f"Erster dynamischer Check. "
                                        f"Verwende initiales Intervall: {next_interval} Sekunden")
                    else:
                        # Für die dynamische Berechnung verwenden wir die aktuellen Daten und die Verlaufsdaten
                        # Wir fügen die Verlaufsdaten zu den aktuellen Daten hinzu
                        current_data = summary.copy()
                        current_data.update(self.history_data)
                        
                        next_interval, time_to_threshold = calculate_next_check_interval(
                            current_data=current_data,
                            threshold_gb=self.threshold_gb,
                            max_interval_seconds=self.max_check_interval_seconds,
                            min_interval_seconds=self.fast_check_interval_seconds
                        )
                        
                        if time_to_threshold is not None:
                            hours = int(time_to_threshold / 3600)
                            minutes = int((time_to_threshold % 3600) / 60)
                            seconds = int(time_to_threshold % 60)
                            
                            if hours > 0:
                                time_str = f"{hours}h {minutes}m {seconds}s"
                            elif minutes > 0:
                                time_str = f"{minutes}m {seconds}s"
                            else:
                                time_str = f"{seconds}s"
                                
                            threshold_time = time.time() + time_to_threshold
                            threshold_time_str = time.strftime("%H:%M:%S", time.localtime(threshold_time))
                            threshold_date_str = time.strftime("%d.%m.%Y", time.localtime(threshold_time))
                            
                            self.logger.info(f"Geschätzte Zeit bis zum Schwellenwert: {time_str} "
                                            f"(voraussichtlich am {threshold_date_str} um {threshold_time_str})")
                    
                    # Aktualisiere das Prüfintervall
                    self.update_check_interval(next_interval)
            else:
                # Alte Logik für nicht-dynamische Intervalle
                if below_threshold and not self.below_threshold:
                    self.below_threshold = True
                    self.update_check_interval(self.fast_check_interval_seconds)
                    self.logger.info(f"Prüfintervall auf {self.fast_check_interval_seconds} Sekunden reduziert")
                elif not below_threshold and self.below_threshold:
                    self.below_threshold = False
                    self.update_check_interval(self.original_check_interval_seconds)
                    self.logger.info(f"Prüfintervall auf ursprünglichen Wert ({self.original_check_interval_seconds} Sekunden) zurückgesetzt")
            
            # Aktionen basierend auf dem Schwellenwert und der Nachbuchungsmöglichkeit
            if below_threshold and kann_nachbuchen:
                self.logger.warning(f"Schwellenwert unterschritten und Nachbuchung möglich! Verbleibendes Volumen: {remaining_gb:.2f} GB")
                
                # Highspeed-Volumen erhöhen
                result = self.increase_highspeed_volume()
                return {
                    "datenvolumen": data_volume,
                    "aktion_erforderlich": True,
                    "aktion_ergebnis": result
                }
            elif below_threshold and not kann_nachbuchen:
                self.logger.warning(f"Schwellenwert unterschritten, aber Nachbuchung nicht möglich! Verbleibendes Volumen: {remaining_gb:.2f} GB")
                
                return {
                    "datenvolumen": data_volume,
                    "aktion_erforderlich": False,
                    "nachricht": "Schwellenwert unterschritten, aber Nachbuchung nicht möglich"
                }
            elif kann_nachbuchen:
                self.logger.info(f"Nachbuchung möglich, obwohl Schwellenwert nicht unterschritten! Verbleibendes Volumen: {remaining_gb:.2f} GB")
                
                # Highspeed-Volumen erhöhen
                result = self.increase_highspeed_volume()
                return {
                    "datenvolumen": data_volume,
                    "aktion_erforderlich": True,
                    "aktion_ergebnis": result
                }
            else:
                self.logger.info(f"Ausreichend Datenvolumen vorhanden und keine Nachbuchung möglich. Keine Aktion erforderlich.")
                return {
                    "datenvolumen": data_volume,
                    "aktion_erforderlich": False
                }
                
        except Exception as e:
            self.logger.error(f"Fehler beim Überprüfen der Verbrauchsdaten: {str(e)}")
            return {"erfolg": False, "nachricht": f"Fehler: {str(e)}"}
    
    def increase_highspeed_volume(self) -> Dict[str, Any]:
        """
        Erhöht das Highspeed-Volumen für den Vertrag.
        
        Returns:
            Ein Dictionary mit dem Ergebnis der Aktion
        """
        self.logger.info(f"Erhöhe Highspeed-Volumen für Vertrag {self.contract_id}")
        
        try:
            result = self.api.increase_highspeed_volume(self.contract_id)
            
            if result.get("erfolg", False):
                self.logger.info(f"Highspeed-Volumen erfolgreich erhöht: {result.get('nachricht', '')}")
                
                # Nach erfolgreicher Erhöhung das Intervall zurücksetzen
                if self.below_threshold:
                    self.below_threshold = False
                    self.update_check_interval(self.original_check_interval_seconds)
                    self.logger.info(f"Prüfintervall nach erfolgreicher Erhöhung auf ursprünglichen Wert ({self.original_check_interval_seconds} Sekunden) zurückgesetzt")
            else:
                self.logger.error(f"Fehler beim Erhöhen des Highspeed-Volumens: {result.get('nachricht', '')}")
                
            return result
        except Exception as e:
            error_msg = f"Fehler beim Erhöhen des Highspeed-Volumens: {str(e)}"
            self.logger.error(error_msg)
            return {"erfolg": False, "nachricht": error_msg}
    
    def update_check_interval(self, seconds: int):
        """
        Aktualisiert das Prüfintervall und passt den Zeitplan an.
        
        Args:
            seconds: Neues Prüfintervall in Sekunden
        """
        with self.interval_lock:  # Lock für die Intervallaktualisierung verwenden
            if not self.running:
                self.check_interval_seconds = seconds
                return
            
            # Bestehenden Job entfernen
            schedule.clear()
            
            # Neuen Job mit aktualisiertem Intervall hinzufügen
            self.check_interval_seconds = seconds
            schedule.every(seconds).seconds.do(self.check_data_usage)
            
            # Berechne und logge den Zeitpunkt des nächsten Abrufs
            next_run_time = time.time() + seconds
            next_run_time_str = time.strftime("%H:%M:%S", time.localtime(next_run_time))
            next_run_date_str = time.strftime("%d.%m.%Y", time.localtime(next_run_time))
            
            self.logger.info(f"Prüfintervall auf {seconds} Sekunden aktualisiert")
            self.logger.info(f"Nächster Abruf geplant für: {next_run_date_str} um {next_run_time_str} (in {seconds} Sekunden)")
    
    def start_monitoring(self):
        """
        Startet die regelmäßige Überwachung der Verbrauchsdaten.
        """
        if self.running:
            self.logger.warning("Überwachung läuft bereits")
            return
        
        if self.guest_url:
            self.contract_id = self.api.get_guest_contract_id()
            
        self.logger.info(f"Starte Überwachung für Vertrag {self.contract_id}")
        self.logger.info(f"Prüfintervall: {self.check_interval_seconds} Sekunde(n)")
        self.logger.info(f"Schwellenwert: {self.threshold_gb} GB")
        self.logger.info(f"Log-Aufbewahrung: {self.log_retention_hours} Stunden")
        
        # Initialen Check durchführen
        initial_data = self.check_data_usage()
        
        # Wenn dynamische Intervallberechnung aktiviert ist, setzen wir das initiale Intervall
        if self.dynamic_interval:
            with self.interval_lock:
                # Beim ersten Start verwenden wir das konfigurierte initiale Intervall
                self.logger.info(f"Dynamische Intervallberechnung aktiviert")
                self.logger.info(f"Initiales Intervall: {self.initial_dynamic_interval_seconds} Sekunde(n)")
                self.logger.info(f"Maximales Intervall: {self.max_check_interval_seconds} Sekunde(n)")
                self.logger.info(f"Minimales Intervall: {self.fast_check_interval_seconds} Sekunde(n)")
                
                # Regelmäßigen Check einrichten mit initialem Intervall
                schedule.every(self.initial_dynamic_interval_seconds).seconds.do(self.check_data_usage)
        else:
            # Regelmäßigen Check einrichten mit konfiguriertem Intervall
            schedule.every(self.check_interval_seconds).seconds.do(self.check_data_usage)
        
        self.running = True
        
        # Hauptschleife für die Überwachung
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Überwachung durch Benutzer unterbrochen")
            self.stop_monitoring()
        except Exception as e:
            self.logger.error(f"Fehler in der Überwachungsschleife: {str(e)}")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """
        Stoppt die Überwachung.
        """
        self.logger.info("Stoppe Überwachung")
        schedule.clear()
        self.running = False


def monitor_data_usage(contract_id: str = None, username: str = None, password: str = None, 
                       guest_url: str = None, threshold_gb: float = None, check_interval_seconds: int = None,
                       log_retention_hours: int = None, fast_check_interval_seconds: int = None,
                       max_check_interval_seconds: int = None, dynamic_interval: bool = None,
                       initial_dynamic_interval_seconds: int = None):
    """
    Hilfsfunktion zum einfachen Starten der Datenüberwachung.
    
    Args:
        contract_id: Die Vertrags-ID, die überwacht werden soll (optional, wird aus .env geladen wenn nicht angegeben)
        username: Benutzername für die Authentifizierung (optional, wird aus .env geladen wenn nicht angegeben)
        password: Passwort für die Authentifizierung (optional, wird aus .env geladen wenn nicht angegeben)
        guest_url: Gast-Link für den Zugriff ohne Anmeldedaten (optional, wird aus .env geladen wenn nicht angegeben)
        threshold_gb: Schwellenwert in GB, bei dem eine Aktion ausgelöst wird (optional, wird aus .env geladen wenn nicht angegeben)
        check_interval_seconds: Intervall in Sekunden, in dem die Daten überprüft werden (optional, wird aus .env geladen wenn nicht angegeben)
        log_retention_hours: Anzahl der Stunden, für die Logs aufbewahrt werden sollen (optional, wird aus .env geladen wenn nicht angegeben)
        fast_check_interval_seconds: Schnelleres Prüfintervall in Sekunden, wenn der Schwellenwert unterschritten wird (optional, wird aus .env geladen wenn nicht angegeben)
        max_check_interval_seconds: Maximales Prüfintervall in Sekunden (optional, wird aus .env geladen wenn nicht angegeben)
        dynamic_interval: Ob das Prüfintervall dynamisch basierend auf der Verbrauchsrate berechnet werden soll (optional, wird aus .env geladen wenn nicht angegeben)
        initial_dynamic_interval_seconds: Initiales Intervall in Sekunden für die dynamische Berechnung (optional, wird aus .env geladen wenn nicht angegeben)
    """
    # Umgebungsvariablen laden
    load_dotenv()
    
    # Werte aus Umgebungsvariablen holen, wenn nicht explizit angegeben
    if contract_id is None:
        env_contract_ids = os.getenv("CONTROL_CENTER_CONTRACT_IDS", "").split(",")
        if env_contract_ids and env_contract_ids[0].strip():
            contract_id = env_contract_ids[0].strip()
        else:
            logger.error("Keine Vertrags-ID angegeben und keine in der .env-Datei gefunden")
            return None
    
    # Prüfe, ob ein Gast-Link angegeben wurde oder in der .env-Datei vorhanden ist
    if guest_url is None:
        guest_url = os.getenv("GUEST_URL", None)
    
    # Prüfe, ob Anmeldedaten oder Gast-Link vorhanden sind
    use_guest_auth = False
    if guest_url:
        use_guest_auth = True
        logger.info("Verwende Gast-Link für die Authentifizierung")
    else:
        # Wenn kein Gast-Link vorhanden ist, prüfe auf Benutzername und Passwort
        if username is None:
            username = os.getenv("CONTROL_CENTER_USERNAME")
        
        if password is None:
            password = os.getenv("CONTROL_CENTER_PASSWORD")
        
        if not username or not password:
            logger.error("Weder vollständige Anmeldedaten noch Gast-Link angegeben oder in der .env-Datei gefunden")
            return None
    
    if threshold_gb is None:
        threshold_gb = float(os.getenv("MONITOR_THRESHOLD_GB", "1.0"))
    
    if check_interval_seconds is None:
        check_interval_seconds = int(os.getenv("MONITOR_CHECK_INTERVAL_SECONDS", "60"))
        
    if log_retention_hours is None:
        log_retention_hours = int(os.getenv("MONITOR_LOG_RETENTION_HOURS", "12"))
        
    if fast_check_interval_seconds is None:
        fast_check_interval_seconds = int(os.getenv("MONITOR_FAST_CHECK_INTERVAL_SECONDS", "5"))
    
    if max_check_interval_seconds is None:
        max_check_interval_seconds = int(os.getenv("MONITOR_MAX_CHECK_INTERVAL_SECONDS", "300"))
        
    if dynamic_interval is None:
        dynamic_interval = os.getenv("MONITOR_DYNAMIC_INTERVAL", "True").lower() in ("true", "1", "yes")
    
    if initial_dynamic_interval_seconds is None:
        initial_dynamic_interval_seconds = int(os.getenv("MONITOR_INITIAL_DYNAMIC_INTERVAL_SECONDS", "60"))
    
    logger.info(f"Starte Überwachung mit folgenden Parametern:")
    logger.info(f"Vertrags-ID: {contract_id}")
    if use_guest_auth:
        logger.info(f"Authentifizierung: Gast-Link")
    else:
        logger.info(f"Authentifizierung: Benutzername/Passwort")
        logger.info(f"Benutzername: {username}")
    logger.info(f"Schwellenwert: {threshold_gb} GB")
    logger.info(f"Normales Prüfintervall: {check_interval_seconds} Sekunde(n)")
    logger.info(f"Schnelles Prüfintervall: {fast_check_interval_seconds} Sekunde(n)")
    logger.info(f"Maximales Prüfintervall: {max_check_interval_seconds} Sekunde(n)")
    logger.info(f"Dynamische Intervallberechnung: {dynamic_interval}")
    if dynamic_interval:
        logger.info(f"Initiales dynamisches Intervall: {initial_dynamic_interval_seconds} Sekunde(n)")
    logger.info(f"Log-Aufbewahrung: {log_retention_hours} Stunden")
    
    # Erstelle den Monitor mit den entsprechenden Parametern
    monitor = DataMonitor(
        contract_id=contract_id,
        username=username if not use_guest_auth else None,
        password=password if not use_guest_auth else None,
        guest_url=guest_url if use_guest_auth else None,
        threshold_gb=threshold_gb,
        check_interval_seconds=check_interval_seconds,
        log_retention_hours=log_retention_hours,
        fast_check_interval_seconds=fast_check_interval_seconds,
        max_check_interval_seconds=max_check_interval_seconds,
        dynamic_interval=dynamic_interval,
        initial_dynamic_interval_seconds=initial_dynamic_interval_seconds
    )
    
    monitor.start_monitoring()
    
    return monitor 