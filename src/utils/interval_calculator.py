"""
Modul zur Berechnung optimaler Überprüfungsintervalle basierend auf Datenverbrauchsraten.
"""

import logging
import time
import datetime
from typing import Dict, Any, Optional, Tuple

# Logger für dieses Modul konfigurieren
logger = logging.getLogger("interval_calculator")

def calculate_next_check_interval(
    current_data: Dict[str, Any],
    threshold_gb: float,
    max_interval_seconds: int = 300,  # 5 Minuten als Standardwert
    min_interval_seconds: int = 30,   # Mindestintervall von 30 Sekunden
    safety_factor: float = 0.7        # Sicherheitsfaktor für die Berechnung
) -> Tuple[int, Optional[float]]:
    """
    Berechnet das optimale Intervall für die nächste Datenverbrauchsprüfung.
    
    Die Funktion berechnet, wann der Schwellenwert basierend auf der aktuellen Verbrauchsrate
    unterschritten wird, und gibt ein entsprechendes Zeitintervall zurück.
    Das Intervall wird mit einem Sicherheitsfaktor (standardmäßig 0,7) multipliziert,
    um sicherzustellen, dass die Überprüfung vor dem Erreichen des Schwellenwerts stattfindet.
    
    Args:
        current_data: Dictionary mit den aktuellen Verbrauchsdaten
        threshold_gb: Schwellenwert in GB, bei dem eine Aktion ausgelöst wird
        max_interval_seconds: Maximales Intervall in Sekunden (Standard: 300 = 5 Minuten)
        min_interval_seconds: Minimales Intervall in Sekunden (Standard: 30 Sekunden)
        safety_factor: Sicherheitsfaktor für die Berechnung (Standard: 0,7)
        
    Returns:
        Tuple mit:
        - Berechnetes Intervall in Sekunden (begrenzt durch min_interval_seconds und max_interval_seconds)
        - Geschätzte Zeit in Sekunden bis zum Erreichen des Schwellenwerts (None, wenn nicht berechenbar)
    """
    # Überprüfen, ob die erforderlichen Daten vorhanden sind
    if not current_data or "datenvolumen" not in current_data:
        logger.warning("Keine gültigen Daten für die Intervallberechnung vorhanden")
        return max_interval_seconds, None
    
    data_volume = current_data["datenvolumen"]
    
    # Aktuelle Werte extrahieren
    verbraucht_gb = data_volume.get("verbraucht_gb", 0)
    highspeed_limit_gb = data_volume.get("highspeed_limit_gb", 0)
    remaining_gb = highspeed_limit_gb - verbraucht_gb
    aktualisiert_timestamp = data_volume.get("aktualisiert_timestamp", time.time())
    
    # Wenn bereits unter dem Schwellenwert, minimales Intervall zurückgeben
    if remaining_gb <= threshold_gb:
        logger.info(f"Bereits unter dem Schwellenwert ({remaining_gb:.2f} GB < {threshold_gb:.2f} GB). "
                   f"Verwende minimales Intervall: {min_interval_seconds} Sekunden")
        return min_interval_seconds, 0
    
    # Verbrauchsrate berechnen, falls historische Daten vorhanden sind
    if "letzte_messung" in current_data and "letzte_messung_zeit" in current_data:
        letzte_verbraucht_gb = current_data["letzte_messung"].get("verbraucht_gb", verbraucht_gb)
        letzte_zeit = current_data["letzte_messung_zeit"]
        
        # Zeit zwischen den Datenaktualisierungen berechnen
        zeit_diff_sekunden = aktualisiert_timestamp - letzte_zeit
        
        # Nur berechnen, wenn genügend Zeit vergangen ist und ein Verbrauch stattgefunden hat
        if zeit_diff_sekunden > 0 and verbraucht_gb > letzte_verbraucht_gb:
            verbrauch_diff_gb = verbraucht_gb - letzte_verbraucht_gb
            verbrauchsrate_gb_pro_sekunde = verbrauch_diff_gb / zeit_diff_sekunden
            
            # Vermeiden von Division durch Null oder sehr kleine Werte
            if verbrauchsrate_gb_pro_sekunde > 0.0000001:
                # Berechnen, wie lange es dauert, bis der Schwellenwert erreicht wird
                # Wir wollen wissen, wie lange es dauert, bis remaining_gb - threshold_gb = 0 ist
                # Also bis remaining_gb = threshold_gb ist
                sekunden_bis_schwellenwert = (remaining_gb - threshold_gb) / verbrauchsrate_gb_pro_sekunde
                
                # Sicherheitsfaktor anwenden
                optimales_intervall = int(sekunden_bis_schwellenwert * safety_factor)
                
                # Formatiere die Verbrauchsrate für bessere Lesbarkeit
                verbrauchsrate_gb_pro_minute = verbrauchsrate_gb_pro_sekunde * 60
                verbrauchsrate_mb_pro_minute = verbrauchsrate_gb_pro_minute * 1024
                
                # Formatiere die Zeit bis zum Schwellenwert für bessere Lesbarkeit
                zeit_bis_schwellenwert = datetime.timedelta(seconds=int(sekunden_bis_schwellenwert))
                schwellenwert_zeitpunkt = datetime.datetime.now() + zeit_bis_schwellenwert
                schwellenwert_zeitpunkt_str = schwellenwert_zeitpunkt.strftime("%d.%m.%Y %H:%M:%S")
                
                logger.info(f"=== Intervallberechnung ===")
                logger.info(f"Aktueller Verbrauch: {verbraucht_gb:.2f} GB von {highspeed_limit_gb:.2f} GB")
                logger.info(f"Verbleibend bis Schwellenwert: {remaining_gb - threshold_gb:.2f} GB")
                logger.info(f"Verbrauchsrate: {verbrauchsrate_gb_pro_minute:.4f} GB/Minute ({verbrauchsrate_mb_pro_minute:.1f} MB/Minute)")
                logger.info(f"Messintervall zwischen Datenaktualisierungen: {zeit_diff_sekunden:.1f} Sekunden")
                logger.info(f"Verbrauch im Messintervall: {verbrauch_diff_gb*1024:.2f} MB")
                logger.info(f"Geschätzte Zeit bis zum Schwellenwert: {zeit_bis_schwellenwert} (voraussichtlich am {schwellenwert_zeitpunkt_str})")
                logger.info(f"Berechnetes optimales Intervall: {optimales_intervall} Sekunden (mit Sicherheitsfaktor {safety_factor})")
                
                # Intervall auf min/max begrenzen
                intervall = max(min(optimales_intervall, max_interval_seconds), min_interval_seconds)
                
                if intervall != optimales_intervall:
                    if intervall == max_interval_seconds:
                        logger.info(f"Intervall auf maximalen Wert von {intervall} Sekunden begrenzt")
                    else:
                        logger.info(f"Intervall auf minimalen Wert von {intervall} Sekunden begrenzt")
                
                return intervall, sekunden_bis_schwellenwert
    
    # Wenn keine Berechnung möglich ist, Standard-Intervall zurückgeben
    logger.info(f"Keine ausreichenden Daten für Verbrauchsratenberechnung. "
               f"Verwende Standard-Intervall: {max_interval_seconds} Sekunden")
    return max_interval_seconds, None 