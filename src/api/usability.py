"""
API-Funktionen für 1&1 Control Center - Verbrauchsdaten
"""

from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime
import re
from bs4 import BeautifulSoup
import time
import random

from curl_cffi.requests import Session

from src.config import BASE_URL
from src.utils.load_proxies import load_proxies
# Importiere ControlCenterAuth nur, wenn es benötigt wird, um zirkuläre Importe zu vermeiden
# from src.auth.login import ControlCenterAuth
from src.utils.logger import setup_logger

# Logger für dieses Modul konfigurieren
logger = setup_logger(__name__)

# Lade die verfügbaren Proxies
loaded_proxies = load_proxies()

def get_random_proxy() -> Dict[str, str]:
    """
    Wählt zufällig einen Proxy aus der Liste aus
    
    Returns:
        Dict[str, str]: Ein zufällig ausgewählter Proxy oder ein leeres Dict für localhost
    """
    if loaded_proxies and len(loaded_proxies) > 0 and loaded_proxies != [{}]:
        return random.choice(loaded_proxies)
    return {}

class ConsumptionAPI:
    """
    API-Klasse für den Zugriff auf Verbrauchsdaten im 1&1 Control Center
    """
    
    def __init__(self, session: Session = None):
        """
        Initialisiert die API-Klasse mit einer bestehenden Session
        
        Args:
            session: Eine bestehende, authentifizierte Session
        """
        self.session = session
        self.base_url = BASE_URL
        self.auth = None
        self.credentials = {"username": None, "password": None, "guest_url": None}
    
    def set_session(self, session: Session = None, username: str = None, password: str = None, guest_url: str = None) -> bool:
        """
        Setzt eine bestehende Session für die API-Anfragen oder führt eine Authentifizierung durch
        
        Diese Methode kann auf drei Arten verwendet werden:
        1. Mit einer bestehenden Session
        2. Mit Benutzername und Passwort, um eine neue Session zu erstellen
        3. Mit einem Gast-Link, um eine neue Gast-Session zu erstellen
        
        Args:
            session: Eine bestehende, authentifizierte Session
            username: Der Benutzername für die Authentifizierung
            password: Das Passwort für die Authentifizierung
            guest_url: Der Gast-Link für die Authentifizierung ohne Anmeldedaten
            
        Returns:
            bool: True, wenn die Session erfolgreich gesetzt oder erstellt wurde, sonst False
        """
        # Fall 1: Eine bestehende Session wurde übergeben
        if session is not None:
            self.session = session
            logger.info(f"Bestehende Session für ConsumptionAPI gesetzt: {id(session)}")
            return True
        
        # Fall 2: Ein Gast-Link wurde übergeben
        elif guest_url is not None:
            logger.info(f"Erstelle neue Gast-Session mit Gast-Link")
            
            # Speichere den Gast-Link für spätere automatische Logins
            self.credentials = {
                "guest_url": guest_url
            }
            
            try:
                # Importiere ControlCenterGuestAuth hier, um zirkuläre Importe zu vermeiden
                from src.auth.login import ControlCenterGuestAuth
                
                # Gast-Authentifizierung durchführen
                self.auth = ControlCenterGuestAuth()
                
                # Erstelle eine neue Session mit Proxy
                proxy = get_random_proxy()
                if proxy:
                    logger.info(f"Verwende Proxy für Gast-Session: {proxy}")
                    self.auth.session = Session(proxies=proxy, impersonate="chrome110")
                else:
                    logger.info("Verwende lokale Verbindung für Gast-Session")
                    self.auth.session = Session(impersonate="chrome110")
                
                session, success = self.auth.get_guest_session(guest_url=guest_url)
                
                if success:
                    self.session = session
                    logger.info(f"Gast-Authentifizierung erfolgreich, neue Session gesetzt: {id(self.session)}")
                    return True
                else:
                    logger.error(f"Gast-Authentifizierung fehlgeschlagen")
                    return False
            except Exception as e:
                logger.error(f"Fehler bei der Gast-Authentifizierung: {str(e)}")
                return False
        
        # Fall 3: Benutzername und Passwort wurden übergeben
        elif username is not None and password is not None:
            logger.info(f"Erstelle neue Session mit Anmeldedaten für Benutzer: {username}")
            
            # Speichere die Anmeldedaten für spätere automatische Logins
            self.credentials = {
                "username": username,
                "password": password
            }
            try:
                # Importiere ControlCenterAuth hier, um zirkuläre Importe zu vermeiden
                from src.auth.login import ControlCenterAuth
                
                # Authentifizierung durchführen
                self.auth = ControlCenterAuth()
                
                # Erstelle eine neue Session mit Proxy
                proxy = get_random_proxy()
                if proxy:
                    logger.info(f"Verwende Proxy für Benutzer-Session: {proxy}")
                    self.auth.session = Session(proxies=proxy, impersonate="chrome110")
                else:
                    logger.info("Verwende lokale Verbindung für Benutzer-Session")
                    self.auth.session = Session(impersonate="chrome110")
                
                session, login_response = self.auth.login(username, password)
                
                if login_response:
                    self.session = session
                    logger.info(f"Authentifizierung erfolgreich, neue Session gesetzt: {id(self.session)}")
                    return True
                else:
                    logger.error(f"Authentifizierung fehlgeschlagen")
                    return False
            except Exception as e:
                logger.error(f"Fehler bei der Authentifizierung: {str(e)}")
                return False
        
        # Fall 4: Weder Session noch Anmeldedaten noch Gast-Link wurden übergeben
        else:
            logger.error("Weder Session noch Anmeldedaten noch Gast-Link wurden übergeben")
            return False
    
    def get_consumption_aggregations(self, contract_id: str) -> Dict[str, Any]:
        """
        Ruft die aggregierten Verbrauchsdaten für einen Vertrag ab
        
        Args:
            contract_id: Die Vertrags-ID
            
        Returns:
            Dict[str, Any]: Die Verbrauchsdaten als Dictionary
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return {}
        
        url = f"{self.base_url}/service/mssa/contracts/{contract_id}/consumption/aggregations"
        
        headers = {
            "X-HR": "true",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": f"{self.base_url}/usages.html",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        try:
            logger.info(f"Rufe Verbrauchsdaten für Vertrag {contract_id} ab")
            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
                impersonate="chrome110"
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Verbrauchsdaten erfolgreich abgerufen")
                
                # Session nach erfolgreicher Anfrage speichern
                if self.auth and self.credentials["username"]:
                    self.auth.save_session(self.credentials["username"])
                
                return data
            elif response.status_code == 403:
                logger.warning("Session ist nicht mehr gültig (403 Forbidden)")
                
                # Versuche, mit gespeicherten Anmeldedaten neu einzuloggen
                if self.credentials["username"] and self.credentials["password"] and self.auth:
                    logger.info("Versuche, mit gespeicherten Anmeldedaten neu einzuloggen")
                    session, login_response = self.auth.login(
                        self.credentials["username"], 
                        self.credentials["password"]
                    )
                    
                    if login_response:
                        self.session = session
                        logger.info("Wiederhole Anfrage nach erfolgreicher Neuanmeldung")
                        return self.get_consumption_aggregations(contract_id)
                
                logger.error("Konnte keine neue Session erstellen")
                return {}
            else:
                logger.warning(f"Fehler beim Abrufen der Verbrauchsdaten: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Verbrauchsdaten: {str(e)}")
            return {}
    
    def parse_data_volume(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert die Datenvolumen-Informationen aus den Verbrauchsdaten
        
        Unterstützt sowohl das Format der regulären Verbrauchsdaten als auch das Format
        der Gast-Verbrauchsdaten.
        
        Args:
            data: Die vollständigen Verbrauchsdaten
            
        Returns:
            Dict[str, Any]: Aufbereitete Datenvolumen-Informationen
        """
        result = {
            "aktualisiert_am": None,
            "aktualisiert_timestamp": None,
            "highspeed_limit_gb": 0,
            "verbraucht_gb": 0,
            "verbraucht_prozent": 0,
            "verbleibend_gb": 0,
            "reset_tag": 1,
            "nachbuchungen": [],
            "kann_nachbuchen": False,
            "nachbuchungs_url": None
        }
        
        try:
            # Prüfen, ob es sich um das Gast-Format handelt
            is_guest_format = "dataVolume" not in data and "highSpeedLimit" in data
            
            # Datenquelle je nach Format auswählen
            if is_guest_format:
                # Gast-Format
                data_volume = data  # Die Daten sind direkt im Hauptobjekt
            else:
                # Reguläres Format
                if "dataVolume" not in data:
                    return result
                data_volume = data["dataVolume"]
            
            # Aktualisierungsdatum parsen
            update_date_key = "dataUpdatedAt"
            if update_date_key in data_volume:
                try:
                    dt = datetime.fromisoformat(data_volume[update_date_key].replace("Z", "+00:00"))
                    result["aktualisiert_am"] = dt.strftime("%d.%m.%Y %H:%M")
                    # Auch als Unix-Timestamp speichern für die Intervallberechnung
                    result["aktualisiert_timestamp"] = dt.timestamp()
                except Exception:
                    result["aktualisiert_am"] = data_volume[update_date_key]
                    # Fallback: Aktuelle Zeit als Timestamp verwenden
                    result["aktualisiert_timestamp"] = time.time()
            
            # Highspeed-Limit
            if "highSpeedLimit" in data_volume and "value" in data_volume["highSpeedLimit"]:
                result["highspeed_limit_gb"] = data_volume["highSpeedLimit"]["value"]
            
            # Verbrauchtes Volumen
            if "totalConsumption" in data_volume and "value" in data_volume["totalConsumption"]:
                result["verbraucht_gb"] = round(data_volume["totalConsumption"]["value"], 2)
            
            # Reset-Tag (nur im regulären Format vorhanden)
            if "resetDay" in data_volume:
                result["reset_tag"] = data_volume["resetDay"]
            
            # Nachgebuchte Pakete verarbeiten
            if "unlimitedRefill" in data_volume:
                unlimited_refill = data_volume["unlimitedRefill"]
                
                # Prüfen, ob Nachbuchung möglich ist (nur im regulären Format)
                if "actions" in unlimited_refill and "refill-highspeed-volume" in unlimited_refill["actions"]:
                    result["kann_nachbuchen"] = True
                    result["nachbuchungs_url"] = unlimited_refill["actions"]["refill-highspeed-volume"].get("href")
                
                # Nachgebuchte Pakete verarbeiten
                if "bookedRefillPackages" in unlimited_refill:
                    refill_packages = unlimited_refill["bookedRefillPackages"]
                    
                    for package in refill_packages:
                        package_info = {
                            "gesamt_gb": 0,
                            "verbraucht_gb": 0,
                        }
                        
                        if "total" in package and "value" in package["total"]:
                            package_info["gesamt_gb"] = round(package["total"]["value"], 2)
                        
                        if "used" in package and "value" in package["used"]:
                            package_info["verbraucht_gb"] = round(package["used"]["value"], 2)
                        
                        result["nachbuchungen"].append(package_info)
            
            # Berechnungen
            if result["highspeed_limit_gb"] > 0:
                result["verbraucht_prozent"] = round((result["verbraucht_gb"] / result["highspeed_limit_gb"]) * 100, 1)
                result["verbleibend_gb"] = round(result["highspeed_limit_gb"] - result["verbraucht_gb"], 2)
            
        except Exception as e:
            logger.error(f"Fehler beim Analysieren der Datenvolumen-Informationen: {str(e)}")
        
        return result
    
    def parse_telephony(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert die Telefonie-Informationen aus den Verbrauchsdaten
        
        Unterstützt sowohl das Format der regulären Verbrauchsdaten als auch das Format
        der Gast-Verbrauchsdaten.
        
        Args:
            data: Die vollständigen Verbrauchsdaten
            
        Returns:
            Dict[str, Any]: Aufbereitete Telefonie-Informationen
        """
        result = {
            "ist_flatrate": False,
            "verbrauchte_sekunden": 0,
            "verbrauchte_minuten": 0,
            "reset_tag": 1
        }
        
        try:
            # Im Gast-Format sind keine Telefonie-Informationen enthalten
            # Prüfen, ob es sich um das Gast-Format handelt
            is_guest_format = "dataVolume" not in data and "highSpeedLimit" in data
            
            # Wenn es das Gast-Format ist, geben wir die Standard-Werte zurück
            if is_guest_format:
                return result
            
            # Reguläres Format
            if "telephony" not in data:
                return result
            
            telephony = data["telephony"]
            
            # Ist Flatrate?
            if "isFlatRate" in telephony:
                result["ist_flatrate"] = telephony["isFlatRate"]
            
            # Verbrauchte Zeit
            if "totalConsumption" in telephony and "value" in telephony["totalConsumption"]:
                result["verbrauchte_sekunden"] = telephony["totalConsumption"]["value"]
                result["verbrauchte_minuten"] = round(result["verbrauchte_sekunden"] / 60, 1)
            
            # Reset-Tag
            if "resetDay" in telephony:
                result["reset_tag"] = telephony["resetDay"]
            
        except Exception as e:
            logger.error(f"Fehler beim Analysieren der Telefonie-Informationen: {str(e)}")
        
        return result
    
    def parse_messages(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert die Nachrichten-Informationen aus den Verbrauchsdaten
        
        Unterstützt sowohl das Format der regulären Verbrauchsdaten als auch das Format
        der Gast-Verbrauchsdaten.
        
        Args:
            data: Die vollständigen Verbrauchsdaten
            
        Returns:
            Dict[str, Any]: Aufbereitete Nachrichten-Informationen
        """
        result = {
            "ist_flatrate": False,
            "anzahl_nachrichten": 0,
            "reset_tag": 1
        }
        
        try:
            # Im Gast-Format sind keine Nachrichten-Informationen enthalten
            # Prüfen, ob es sich um das Gast-Format handelt
            is_guest_format = "dataVolume" not in data and "highSpeedLimit" in data
            
            # Wenn es das Gast-Format ist, geben wir die Standard-Werte zurück
            if is_guest_format:
                return result
            
            # Reguläres Format
            if "messages" not in data:
                return result
            
            messages = data["messages"]
            
            # Ist Flatrate?
            if "isFlatRate" in messages:
                result["ist_flatrate"] = messages["isFlatRate"]
            
            # Anzahl Nachrichten
            if "totalConsumption" in messages and "value" in messages["totalConsumption"]:
                result["anzahl_nachrichten"] = int(messages["totalConsumption"]["value"])
            
            # Reset-Tag
            if "resetDay" in messages:
                result["reset_tag"] = messages["resetDay"]
            
        except Exception as e:
            logger.error(f"Fehler beim Analysieren der Nachrichten-Informationen: {str(e)}")
        
        return result
    
    def get_consumption_summary(self, contract_id: str) -> Dict[str, Any]:
        """
        Ruft eine Zusammenfassung der Verbrauchsdaten für einen Vertrag ab
        
        Entscheidet anhand des Vorhandenseins des 'ciam-ust'-Cookies, ob die normale
        oder die Gast-Version der get_consumption_aggregations Methode verwendet wird.
        
        Args:
            contract_id: Die Vertrags-ID
            
        Returns:
            Dict[str, Any]: Eine Zusammenfassung der Verbrauchsdaten
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return {
                "erfolg": False,
                "fehlermeldung": "Keine Session vorhanden"
            }
            
        # Prüfe, ob das 'ciam-ust'-Cookie vorhanden ist
        has_ciam_ust_cookie = False
        
        if hasattr(self.session, 'cookies'):
            # Versuche, das Cookie aus verschiedenen Cookie-Formaten zu extrahieren
            if hasattr(self.session.cookies, 'get'):
                has_ciam_ust_cookie = self.session.cookies.get('ciam-ust') is not None
            elif hasattr(self.session.cookies, '__getitem__'):
                try:
                    has_ciam_ust_cookie = 'ciam-ust' in self.session.cookies
                except (KeyError, TypeError):
                    pass
            else:
                # Iteriere über Cookies, falls es eine Liste/Sammlung ist
                try:
                    for cookie in self.session.cookies:
                        if hasattr(cookie, 'name') and cookie.name == 'ciam-ust':
                            has_ciam_ust_cookie = True
                            break
                except Exception as e:
                    logger.warning(f"Fehler beim Durchsuchen der Cookies: {str(e)}")
        
        # Rufe die Rohdaten ab, je nach Session-Typ
        if has_ciam_ust_cookie:
            data = self.get_consumption_aggregations(contract_id)
        else:
            data = self.get_guest_consumption_aggregations(contract_id)
        
        if not data:
            logger.warning("Keine Verbrauchsdaten verfügbar")
            return {
                "erfolg": False,
                "fehlermeldung": "Keine Verbrauchsdaten verfügbar"
            }
        
        # Analysiere die Daten
        result = {
            "erfolg": True,
            "vertrag_id": contract_id,
            "datenvolumen": self.parse_data_volume(data),
            "telefonie": self.parse_telephony(data),
            "nachrichten": self.parse_messages(data),
            "gesamtkosten": None
        }
        
        # Gesamtkosten
        if "totalCosts" in data:
            result["gesamtkosten"] = {
                "betrag": data["totalCosts"].get("amount", "0,00"),
                "währung": data["totalCosts"].get("currency", "EUR")
            }
        
        return result
        
    def _request_unlimited_highspeed(self) -> Optional[str]:
        """
        Sendet eine Anfrage an die Unlimited-Highspeed-Seite und gibt den HTML-Inhalt zurück
        
        Returns:
            Optional[str]: Der HTML-Inhalt der Unlimited-Highspeed-Seite oder None bei einem Fehler
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return None
            
        try:
            logger.info("Hole HTML-Inhalt von der Unlimited-Highspeed-Seite")
            url = f"{self.base_url}/unlimited-highspeed"
            
            headers = {
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"macOS\"",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
                impersonate="chrome110"
            )
            
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Unlimited-Highspeed-Seite: {response.status_code}")
                return None
                
            return response.text
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Unlimited-Highspeed-Seite: {str(e)}")
            return None

    def _request_usages_page(self) -> Optional[str]:
        """
        Sendet eine Anfrage an die Usages-Seite und gibt den HTML-Inhalt zurück
        
        Returns:
            Optional[str]: Der HTML-Inhalt der Usages-Seite oder None bei einem Fehler
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return None
            
        try:
            logger.info("Hole HTML-Inhalt von der Usages-Seite")
            url = f"{self.base_url}/usages.html"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"macOS\"",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
                impersonate="chrome110"
            )
            
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Usages-Seite: {response.status_code}")
                return None
                
            return response.text
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Usages-Seite: {str(e)}")
            return None
    
    def _extract_csrf_token(self, html_content: str) -> Optional[str]:
        """
        Extrahiert das CSRF-Token aus dem HTML-Inhalt der Usages-Seite
        
        Args:
            html_content: Der HTML-Inhalt der Usages-Seite
            
        Returns:
            Optional[str]: Das CSRF-Token oder None, wenn es nicht gefunden wurde
        """
        if not html_content:
            logger.error("Kein HTML-Inhalt zum Extrahieren des CSRF-Tokens vorhanden")
            return None
            
        try:
            # HTML-Inhalt mit BeautifulSoup parsen
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # CSRF-Token aus dem Meta-Tag extrahieren
            csrf_meta = soup.find('meta', {'name': '_csrf'})
            if csrf_meta and 'content' in csrf_meta.attrs:
                csrf_token = csrf_meta.attrs['content']
                logger.info(f"CSRF-Token erfolgreich extrahiert: {csrf_token[:10]}...")
                return csrf_token
                
            # Alternativ: Versuche, das Token mit einem regulären Ausdruck zu finden
            if not csrf_meta:
                logger.info("Versuche, CSRF-Token mit regulärem Ausdruck zu finden")
                match = re.search(r'<meta name="_csrf" content="([^"]+)"', html_content)
                if match:
                    csrf_token = match.group(1)
                    logger.info(f"CSRF-Token erfolgreich mit Regex extrahiert: {csrf_token[:10]}...")
                    return csrf_token
            
            logger.error("CSRF-Token konnte nicht gefunden werden")
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren des CSRF-Tokens: {str(e)}")
            return None
    
    def get_csrf_token(self) -> Optional[str]:
        """
        Holt das CSRF-Token aus der Unlimited-Highspeed-Seite oder der Usages-Seite
        
        Returns:
            Optional[str]: Das CSRF-Token oder None bei einem Fehler
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return None
            
        # Prüfe, ob wir das ciam-ust-Cookie haben
        has_ciam_ust_cookie = False
        if hasattr(self.session, 'cookies') and self.session.cookies:
            # Versuche, das Cookie aus verschiedenen Cookie-Formaten zu extrahieren
            if hasattr(self.session.cookies, 'get'):
                has_ciam_ust_cookie = self.session.cookies.get('ciam-ust') is not None
            elif hasattr(self.session.cookies, '__getitem__'):
                try:
                    has_ciam_ust_cookie = 'ciam-ust' in self.session.cookies
                except (KeyError, TypeError):
                    pass
            else:
                # Iteriere über Cookies, falls es eine Liste/Sammlung ist
                try:
                    for cookie in self.session.cookies:
                        if hasattr(cookie, 'name') and cookie.name == 'ciam-ust':
                            has_ciam_ust_cookie = True
                            break
                except Exception as e:
                    logger.warning(f"Fehler beim Durchsuchen der Cookies: {str(e)}")
        
        # Hole den HTML-Inhalt der entsprechenden Seite
        if has_ciam_ust_cookie:
            html_content = self._request_usages_page()
        else:
            html_content = self._request_unlimited_highspeed()
            
        if not html_content:
            return None
            
        # Extrahiere das CSRF-Token aus dem HTML-Inhalt
        return self._extract_csrf_token(html_content)

    def get_guest_contract_id(self) -> Optional[str]:
        """
        Extrahiert die Vertrags-ID aus dem HTML-Body-Tag der Unlimited-Highspeed-Seite
        
        Diese Methode sendet eine Anfrage an die Unlimited-Highspeed-Seite und extrahiert
        die Vertrags-ID aus dem data-contract-id Attribut des body-Tags.
        
        Returns:
            Optional[str]: Die Vertrags-ID oder None bei einem Fehler
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return None
            
        try:
            # Hole den HTML-Inhalt der Unlimited-Highspeed-Seite
            html_content = self._request_unlimited_highspeed()
            
            if not html_content:
                logger.error("Konnte keinen HTML-Inhalt von der Unlimited-Highspeed-Seite abrufen")
                return None
                
            # Verwende BeautifulSoup, um die Vertrags-ID aus dem body-Tag zu extrahieren
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            body_tag = soup.find('body')
            
            if not body_tag or not body_tag.has_attr('data-contract-id'):
                logger.error("Konnte keine Vertrags-ID im body-Tag finden")
                return None
                
            contract_id = body_tag['data-contract-id']
            logger.info(f"Vertrags-ID aus HTML-Body-Tag extrahiert: {contract_id}")
            
            return contract_id
            
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der Vertrags-ID: {str(e)}")
            return None

    def increase_highspeed_volume(self, contract_id: str) -> Dict[str, Any]:
        """
        Erhöht das Highspeed-Datenvolumen um 1GB
        
        Unterstützt sowohl normale Benutzeranmeldungen als auch Gast-Links.
        
        Args:
            contract_id: Die Vertrags-ID
            
        Returns:
            Dict[str, Any]: Ergebnis der Anfrage
                - erfolg: True, wenn die Anfrage erfolgreich war
                - status_code: HTTP-Statuscode der Antwort
                - nachricht: Nachricht vom Server oder Fehlermeldung
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return {
                "erfolg": False,
                "status_code": None,
                "nachricht": "Keine Session vorhanden"
            }
        
        # CSRF-Token von der Usages-Seite holen
        csrf_token = self.get_csrf_token()
        
        if not csrf_token:
            logger.error("CSRF-Token konnte nicht extrahiert werden")
            return {
                "erfolg": False,
                "status_code": None,
                "nachricht": "CSRF-Token konnte nicht extrahiert werden"
            }
        
        url = f"{self.base_url}/service/mssa/contracts/{contract_id}/consumption/highspeed-volume"
        
        headers = {
            "X-HR": "true",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "Origin": f"{self.base_url}",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": f"{self.base_url}/usages.html",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "X-CSRF-TOKEN": csrf_token
        }
        
        try:
            logger.info(f"Erhöhe Highspeed-Datenvolumen für Vertrag {contract_id}")
            response = self.session.post(
                url,
                headers=headers,
                timeout=30,
                impersonate="chrome110"
            )
            
            result = {
                "status_code": response.status_code
            }
            
            if response.status_code == 204:
                logger.info(f"Highspeed-Datenvolumen erfolgreich um 1GB erhöht")
                result["erfolg"] = True
                result["nachricht"] = "Datenvolumen wurde erfolgreich um 1GB erhöht"
                
                # Session nach erfolgreicher Anfrage speichern
                if self.auth:
                    if "username" in self.credentials and self.credentials["username"]:
                        self.auth.save_session(self.credentials["username"])
                    elif "guest_url" in self.credentials and self.credentials["guest_url"]:
                        # Für Gast-URLs extrahieren wir die Gast-ID und speichern die Session
                        import re
                        token_match = re.search(r'/mc/([^/]+)', self.credentials["guest_url"])
                        if token_match:
                            guest_id = f"guest_{token_match.group(1)}"
                            logger.info(f"Speichere Gast-Session für ID: {guest_id}")
                            self.auth.save_session(guest_id)
                        else:
                            logger.warning("Konnte keine Gast-ID aus der URL extrahieren")
            elif response.status_code == 400:
                logger.warning(f"Datenvolumen kann noch nicht erhöht werden (nicht freigeschaltet)")
                result["erfolg"] = False
                result["nachricht"] = "Datenvolumen kann noch nicht erhöht werden (nicht freigeschaltet)"
            elif response.status_code == 403:
                logger.warning("Session ist nicht mehr gültig (403 Forbidden)")
                result["erfolg"] = False
                result["nachricht"] = "Session ist abgelaufen"
                
                # Versuche, mit gespeicherten Anmeldedaten neu einzuloggen
                if self.auth:
                    if "username" in self.credentials and self.credentials["username"] and "password" in self.credentials and self.credentials["password"]:
                        # Normale Benutzeranmeldung
                        logger.info("Versuche, mit gespeicherten Anmeldedaten neu einzuloggen")
                        session, login_response = self.auth.login(
                            self.credentials["username"], 
                            self.credentials["password"]
                        )
                        
                        if login_response:
                            self.session = session
                            logger.info("Wiederhole Anfrage nach erfolgreicher Neuanmeldung")
                            return self.increase_highspeed_volume(contract_id)
                    elif "guest_url" in self.credentials and self.credentials["guest_url"]:
                        # Gast-Link
                        logger.info("Versuche, mit Gast-Link neu einzuloggen")
                        session, success = self.auth.get_guest_session(guest_url=self.credentials["guest_url"])
                        
                        if success:
                            self.session = session
                            logger.info("Wiederhole Anfrage nach erfolgreicher Gast-Neuanmeldung")
                            return self.increase_highspeed_volume(contract_id)
            else:
                logger.warning(f"Fehler beim Erhöhen des Datenvolumens: {response.status_code}")
                result["erfolg"] = False
                result["nachricht"] = f"Fehler beim Erhöhen des Datenvolumens: {response.status_code}"
            
            return result
                
        except Exception as e:
            logger.error(f"Fehler beim Erhöhen des Datenvolumens: {str(e)}")
            return {
                "erfolg": False,
                "status_code": None,
                "nachricht": f"Fehler: {str(e)}"
            }
        
    def get_guest_consumption_aggregations(self, contract_id: str) -> Dict[str, Any]:
        """
        Ruft die Verbrauchsdaten für eine Gast-Session ab
        
        Diese Methode sendet eine Anfrage an den Endpunkt für Verbrauchsdaten mit den
        spezifischen Headers für eine Gast-Session.
        
        Args:
            contract_id: Die Vertrags-ID, für die die Verbrauchsdaten abgerufen werden sollen
            
        Returns:
            Dict[str, Any]: Die Verbrauchsdaten oder ein leeres Dictionary bei einem Fehler
        """
        if not self.session:
            logger.error("Keine Session vorhanden. Bitte zuerst set_session() aufrufen.")
            return {}
            
        try:
            # Hole das CSRF-Token
            #csrf_token = self.get_csrf_token()
            #if not csrf_token:
            #    logger.error("Konnte kein CSRF-Token für die Anfrage erhalten")
            #    return {}
                
            # Erstelle die URL für die Anfrage
            url = f"{self.base_url}/service/mssa/contracts/{contract_id}/consumption/aggregations/data-volume-for-landingpage"
            
            # Spezifische Headers für diese Anfrage
            headers = {
                "Connection": "keep-alive",
                #"X-HR": "true",
                "sec-ch-ua-platform": "\"macOS\"",
                #"X-CSRF-TOKEN": csrf_token,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
                "sec-ch-ua-mobile": "?0",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://control-center.1und1.de/unlimited-highspeed",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            # Sende die Anfrage
            logger.info(f"Rufe Verbrauchsdaten für Gast-Session ab (Vertrags-ID: {contract_id})")
            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
                impersonate="chrome110"
            )
            
            # Prüfe, ob die Anfrage erfolgreich war
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Verbrauchsdaten: {response.status_code}")
                return {}
                
            # Versuche, die Antwort als JSON zu parsen
            try:
                data = response.json()
                logger.info("Verbrauchsdaten erfolgreich abgerufen")
                return data
            except ValueError as e:
                logger.error(f"Fehler beim Parsen der Verbrauchsdaten: {str(e)}")
                return {}
                
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Verbrauchsdaten: {str(e)}")
            return {}
        