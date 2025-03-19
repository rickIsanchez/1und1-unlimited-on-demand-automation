"""
Authentifizierungsmodul für 1&1 Control Center
"""

import re
import os
import pickle
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime

from src.config import BASE_URL
from src.utils.http_handler import HttpClient
from src.utils.logger import setup_logger
from dotenv import load_dotenv

# Logger für dieses Modul konfigurieren
logger = setup_logger(__name__)

class ControlCenterAuth:
    """
    Authentifizierungsklasse für 1&1 Control Center
    """
    
    # Statische Klassenvariable für den Pfad zur Session-Datei
    SESSION_FILE = os.path.join(os.path.expanduser("~"), ".1und1_sessions.pickle")
    
    def __init__(self):
        # Erstelle einen HTTP-Client mit einer dedizierten Session
        self.http_client = HttpClient()
        # Stelle sicher, dass wir eine frische Session haben
        self.session = self.http_client.session
        self.is_authenticated = False
        self.session_data = {}
        self.username = None
        
        # Initialisiere die Session mit den Standard-Headers
        logger.info("Initialisiere neue Session für den Authentifizierungsprozess")
        
    def initialize_session(self) -> None:
        """
        Initialisiert eine neue Session für den Authentifizierungsprozess.
        Diese Methode sollte aufgerufen werden, bevor der Login-Flow beginnt.
        """
        logger.info("Erstelle neue Session für den Authentifizierungsprozess")
        
        # Erstelle eine neue Session im HTTP-Client
        self.http_client = HttpClient()
        self.session = self.http_client.session
        self.is_authenticated = False
        self.session_data = {}
        
        return self.session
        
    def get_oauth_authorization_url(self, max_redirects: int = 10) -> Tuple[Any, Any]:
        """
        Initiiert den OAuth2-Autorisierungsprozess und verfolgt alle Weiterleitungen.
        
        Diese Methode sendet eine Anfrage an den OAuth2-Autorisierungsendpunkt und verfolgt
        alle Weiterleitungen manuell, um die vollständige Weiterleitungskette zu erfassen.
        Dabei wird die Session-Verwaltung von curl_cffi genutzt.
        
        Args:
            max_redirects: Maximale Anzahl der zu verfolgenden Weiterleitungen (Standardwert: 10)
            
        Returns:
            Tuple[Session, Response]: 
                - Die aktive Session
                - Die Response des letzten Requests
        """
        logger.info("Starte OAuth2-Autorisierungsprozess mit Verfolgung aller Weiterleitungen")
        
        # Stelle sicher, dass wir eine aktive Session haben
        if not hasattr(self, 'session') or self.session is None:
            self.initialize_session()
        
        auth_url = f"{BASE_URL}/oauth2/authorization/authorization-code-grant"
        
        # Spezifische Headers für diese Anfrage
        headers = {
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
            "Accept-Language": "de-DE,de;q=0.9"
        }
        
        try:
            # Verwende die Session direkt aus der Klasse
            logger.debug(f"Verwende Session: {id(self.session)}")
            
            # Erste Anfrage mit allow_redirects=True, aber max_redirects begrenzen
            response = self.session.get(
                auth_url,
                headers=headers,
                timeout=30,
                impersonate="chrome110",
                allow_redirects=True,
                max_redirects=max_redirects
            )
            
            if 'control_center_web_bap' in response.url:
                logger.info(f"OAuth2-Autorisierungsprozess abgeschlossen.")
            else:
                logger.error(f"OAuth2-Autorisierungsprozess nicht abgeschlossen.")
            
            # Gib die Session und die Response zurück
            return self.session, response
                
        except Exception as e:
            logger.error(f"Fehler beim Verfolgen der OAuth2-Weiterleitungen: {str(e)}")
            return self.session, None
    
    def extract_form_data(self, html_content: str) -> Dict[str, Any]:
        """
        Extrahiert alle Formularfelder aus einem HTML-Inhalt.
        
        Diese Methode analysiert den HTML-Inhalt und extrahiert alle Input-Felder,
        insbesondere versteckte Felder, sowie die Formular-Action-URL.
        
        Args:
            html_content: Der HTML-Inhalt, der analysiert werden soll
            
        Returns:
            Dict[str, Any]: Ein Dictionary mit den extrahierten Daten:
                - 'inputs': Ein Dictionary mit allen Input-Feldern (Name -> Wert)
                - 'action': Die Action-URL des Formulars
                - 'method': Die HTTP-Methode des Formulars (GET/POST)
        """
        from bs4 import BeautifulSoup
        
        result = {
            'inputs': {},
            'action': None,
            'method': 'POST'  # Standardwert
        }
        
        try:
            # Verwende BeautifulSoup für robustes HTML-Parsing
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Finde das Hauptformular (in diesem Fall das Login-Formular)
            form = soup.find('form', id='kc-form-login')
            if not form:
                # Fallback: Suche nach einem beliebigen Formular
                form = soup.find('form')
            
            if form:
                # Extrahiere die Action-URL und Methode
                result['action'] = form.get('action')
                result['method'] = form.get('method', 'POST').upper()
                
                # Extrahiere alle Input-Felder
                for input_field in form.find_all('input'):
                    name = input_field.get('name')
                    value = input_field.get('value', '')
                    
                    if name:
                        result['inputs'][name] = value
                        
                        # Protokolliere versteckte Felder für Debugging
                        if input_field.get('type') == 'hidden':
                            logger.debug(f"Verstecktes Feld gefunden: {name}={value}")
            else:
                logger.warning("Kein Formular im HTML-Inhalt gefunden")
                
                # Fallback: Verwende Regex, um Input-Felder zu finden
                input_pattern = r'<input[^>]*name=["\']([^"\']*)["\'][^>]*(?:value=["\']([^"\']*)["\'])?'
                inputs = re.findall(input_pattern, html_content)
                
                for name, value in inputs:
                    result['inputs'][name] = value
                
                # Versuche, die Action-URL zu finden
                action_pattern = r'<form[^>]*action=["\']([^"\']*)["\']'
                action_match = re.search(action_pattern, html_content)
                if action_match:
                    result['action'] = action_match.group(1)
                
                # Versuche, die Methode zu finden
                method_pattern = r'<form[^>]*method=["\']([^"\']*)["\']'
                method_match = re.search(method_pattern, html_content)
                if method_match:
                    result['method'] = method_match.group(1).upper()
        
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der Formulardaten: {str(e)}")
        
        return result
    
    def _create_serializable_session_data(self) -> Dict[str, Any]:
        """
        Erstellt eine serialisierbare Kopie der wichtigen Session-Daten
        
        Returns:
            Dict[str, Any]: Ein Dictionary mit den serialisierbaren Session-Daten
        """
        if not self.session:
            return {}
            
        # Extrahiere das Cookie-Jar-Objekt, falls vorhanden
        cookies_jar = None
        if hasattr(self.session, 'cookies') and hasattr(self.session.cookies, 'jar'):
            if hasattr(self.session.cookies.jar, '_cookies'):
                cookies_jar = self.session.cookies.jar._cookies
        
        # Extrahiere Headers
        headers_dict = {}
        if hasattr(self.session, 'headers'):
            headers_dict = dict(self.session.headers)
        
        # Erstelle serialisierbare Session-Daten
        return {
            "cookies_jar": cookies_jar,
            "headers": headers_dict,
            "timestamp": datetime.now().isoformat()
        }
    
    def _restore_session_from_data(self, session_data: Dict[str, Any]) -> bool:
        """
        Stellt eine Session aus gespeicherten Daten wieder her
        
        Args:
            session_data: Die gespeicherten Session-Daten
            
        Returns:
            bool: True, wenn die Session erfolgreich wiederhergestellt wurde, sonst False
        """
        if not session_data or not isinstance(session_data, dict):
            return False
            
        try:
            # Initialisiere eine neue Session, falls nötig
            if not self.session:
                self.initialize_session()
            
            # Stelle das Cookie-Jar-Objekt wieder her, falls vorhanden
            if "cookies_jar" in session_data and session_data["cookies_jar"] is not None:
                self.session.cookies.jar._cookies.update(session_data["cookies_jar"])
            
            # Stelle Headers wieder her
            if "headers" in session_data and isinstance(session_data["headers"], dict):
                self.session.headers.update(session_data["headers"])
                
            return True
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen der Session: {str(e)}")
            return False
    
    def save_session(self, username: str) -> bool:
        """
        Speichert die aktuelle Session in einer Datei
        
        Args:
            username: Der Benutzername, für den die Session gespeichert wird
            
        Returns:
            bool: True, wenn die Session erfolgreich gespeichert wurde, sonst False
        """
        if not self.session:
            logger.warning("Keine Session zum Speichern vorhanden")
            return False
            
        try:
            # Erstelle das Verzeichnis, falls es nicht existiert
            os.makedirs(os.path.dirname(self.SESSION_FILE), exist_ok=True)
            
            # Lade bestehende Sessions, falls vorhanden
            sessions = {}
            if os.path.exists(self.SESSION_FILE) and os.path.getsize(self.SESSION_FILE) > 0:
                try:
                    with open(self.SESSION_FILE, "rb") as f:
                        sessions = pickle.load(f)
                    
                    # Prüfe, ob sessions ein Dictionary ist
                    if not isinstance(sessions, dict):
                        logger.warning("Gespeicherte Sessions haben ein ungültiges Format, erstelle neue Sessions")
                        sessions = {}
                except (EOFError, pickle.UnpicklingError) as e:
                    logger.warning(f"Fehler beim Laden bestehender Sessions: {str(e)}")
                    # Wenn die Datei beschädigt ist, erstellen wir ein neues Sessions-Dictionary
                    sessions = {}
                except Exception as e:
                    logger.warning(f"Unerwarteter Fehler beim Laden bestehender Sessions: {str(e)}")
                    sessions = {}
            
            # Erstelle serialisierbare Session-Daten
            session_data = self._create_serializable_session_data()

            # Füge die aktuelle Session hinzu oder aktualisiere sie
            sessions[username] = session_data
            
            # Speichere alle Sessions
            # Erstelle zuerst eine temporäre Datei
            temp_file = f"{self.SESSION_FILE}.tmp"
            with open(temp_file, "wb") as f:
                pickle.dump(sessions, f)
            
            # Prüfe, ob die temporäre Datei erfolgreich erstellt wurde
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                # Ersetze die alte Datei durch die neue
                if os.path.exists(self.SESSION_FILE):
                    os.remove(self.SESSION_FILE)
                os.rename(temp_file, self.SESSION_FILE)
                # logger.info(f"Session für Benutzer {username} erfolgreich gespeichert")
                return True
            else:
                logger.error("Fehler beim Erstellen der temporären Session-Datei")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Session: {str(e)}")
            return False
    
    def load_session(self, username: str) -> bool:
        """
        Lädt eine gespeicherte Session für einen Benutzer
        
        Args:
            username: Der Benutzername, für den die Session geladen werden soll
            
        Returns:
            bool: True, wenn die Session erfolgreich geladen wurde, sonst False
        """
        try:
            # Prüfe, ob die Session-Datei existiert
            if not os.path.exists(self.SESSION_FILE):
                logger.info("Keine gespeicherte Session gefunden")
                return False
                
            # Prüfe, ob die Datei leer ist
            if os.path.getsize(self.SESSION_FILE) == 0:
                logger.warning("Session-Datei ist leer, entferne sie")
                os.remove(self.SESSION_FILE)
                return False
                
            # Lade die Sessions
            try:
                with open(self.SESSION_FILE, "rb") as f:
                    sessions = pickle.load(f)
            except (EOFError, pickle.UnpicklingError) as e:
                logger.warning(f"Fehler beim Laden der Session: {str(e)}")
                # Wenn die Datei beschädigt ist, entferne sie
                os.remove(self.SESSION_FILE)
                return False
                
            # Prüfe, ob die geladenen Daten ein Dictionary sind
            if not isinstance(sessions, dict):
                logger.warning("Gespeicherte Sessions haben ein ungültiges Format")
                os.remove(self.SESSION_FILE)
                return False
                
            # Prüfe, ob eine Session für den Benutzer existiert
            if username not in sessions:
                logger.info(f"Keine gespeicherte Session für Benutzer {username} gefunden")
                return False
                
            # Hole die Session-Daten
            session_data = sessions[username]

            # Stelle die Session wieder her
            if not self._restore_session_from_data(session_data):
                logger.warning("Konnte Session nicht wiederherstellen")
                return False
                
            # Prüfe, ob die Session noch gültig ist
            if not self.is_session_valid():
                logger.info("Gespeicherte Session ist nicht mehr gültig, führe neuen Login durch")
                return False
                
            logger.info(f"Session für Benutzer {username} erfolgreich geladen")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Session: {str(e)}")
            return False
    
    def is_session_valid(self) -> bool:
        """
        Überprüft, ob die aktuelle Session noch gültig ist.
        
        Diese Methode versucht, eine Anfrage an das Control Center zu senden,
        um zu prüfen, ob die Session noch gültig ist.
        
        Returns:
            bool: True, wenn die Session gültig ist, sonst False
        """
        if not self.session:
            logger.warning("Keine Session zum Validieren vorhanden")
            return False
            
        try:
            # Prüfe, ob das 'ciam-ust'-Cookie vorhanden ist
            has_ciam_cookie = False
            
            # Verschiedene Möglichkeiten, das Cookie zu finden
            if hasattr(self.session.cookies, 'get'):
                # RequestsCookieJar hat eine get-Methode
                has_ciam_cookie = self.session.cookies.get('ciam-ust') is not None
            elif hasattr(self.session.cookies, '__getitem__'):
                # Dictionary-ähnlicher Zugriff
                try:
                    has_ciam_cookie = 'ciam-ust' in self.session.cookies
                except (KeyError, TypeError):
                    pass
            else:
                # Iteriere über Cookies, falls es eine Liste/Sammlung ist
                try:
                    for cookie in self.session.cookies:
                        if isinstance(cookie, str) and cookie == 'ciam-ust':
                            has_ciam_cookie = True
                            break
                        elif hasattr(cookie, 'name') and cookie.name == 'ciam-ust':
                            has_ciam_cookie = True
                            break
                except Exception as e:
                    logger.warning(f"Fehler beim Durchsuchen der Cookies: {str(e)}")
            
            if has_ciam_cookie:
                # Normale Benutzer-Session: Verwende ConsumptionAPI für die Validierung
                from src.api.usability import ConsumptionAPI
                from src.config import get_primary_contract_id
                
                # Hole die primäre Vertrags-ID
                contract_id = get_primary_contract_id()
                
                # Erstelle ConsumptionAPI-Instanz mit der aktuellen Session
                api = ConsumptionAPI(self.session)
                
                # Rufe die Verbrauchsdaten ab
                data = api.get_consumption_aggregations(contract_id)
                
                # Wenn Daten zurückgegeben wurden, ist die Session gültig
                if data:
                    logger.info("Session ist gültig (Verbrauchsdaten erfolgreich abgerufen)")
                    return True
                else:
                    logger.warning("Session ist nicht mehr gültig (keine Daten erhalten)")
                    return False
            else:
                # Gast-Session: Verwende get_guest_contract_id für die Validierung
                from src.api.usability import ConsumptionAPI
                
                # Erstelle ConsumptionAPI-Instanz mit der aktuellen Session
                api = ConsumptionAPI(self.session)
                
                # Versuche, die Gast-Vertrags-ID zu erhalten
                contract_id = api.get_guest_contract_id()
                
                # Wenn eine Vertrags-ID zurückgegeben wurde, ist die Session gültig
                if contract_id:
                    logger.info("Gast-Session ist gültig (Vertrags-ID erfolgreich abgerufen)")
                    return True
                else:
                    logger.warning("Gast-Session ist nicht mehr gültig (keine Vertrags-ID erhalten)")
                    return False
                
        except Exception as e:
            logger.error(f"Fehler bei der Session-Validierung: {str(e)}")
            return False
    
    def login(self, username: str, password: str) -> Tuple[Any, Any]:
        """
        Führt den Login-Prozess mit Benutzername und Passwort durch.
        
        Diese Methode initiiert den OAuth2-Autorisierungsprozess, extrahiert die Formulardaten
        aus der Antwort und sendet dann eine POST-Anfrage mit den Anmeldedaten.
        
        Args:
            username: Der Benutzername (E-Mail-Adresse)
            password: Das Passwort
            
        Returns:
            Tuple[Any, Any]:
                - Die authentifizierte Session
                - Die Antwort des Servers
        """
        # Versuche zuerst, eine gespeicherte Session zu laden
        if self.load_session(username):
            logger.info(f"Gespeicherte Session für Benutzer {username} geladen")
            return self.session, True

        
        logger.info(f"Starte Login-Prozess für Benutzer: {username}")
        
        # Initialisiere eine neue Session für den Login-Prozess
        self.initialize_session()
        self.username = username
        
        try:
            # Schritt 1: Initiiere den OAuth2-Autorisierungsprozess
            session, response = self.get_oauth_authorization_url()
            
            if not response:
                logger.error("Konnte keine Antwort vom OAuth2-Autorisierungsendpunkt erhalten")
                return self.session, None
            
            # Schritt 2: Extrahiere die Formulardaten aus der Antwort
            form_data = self.extract_form_data(response.text)
            
            if not form_data['action']:
                logger.error("Konnte keine Action-URL aus dem Formular extrahieren")
                return self.session, None
            
            # Schritt 3: Bereite die Anmeldedaten vor
            login_data = form_data['inputs'].copy()
            
            # Füge Benutzername und Passwort hinzu
            login_data['username'] = username
            login_data['password'] = password
            
            # Stelle sicher, dass credentialId vorhanden ist (falls erforderlich)
            if 'credentialId' not in login_data and 'credentialId' in form_data['inputs']:
                login_data['credentialId'] = form_data['inputs']['credentialId']
            
            logger.debug(f"Sende Login-Anfrage an: {form_data['action']}")
            
            # Schritt 4: Sende die POST-Anfrage mit den Anmeldedaten
            login_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"macOS\"",
                "Accept-Language": "de-DE,de;q=0.9"
            }
            
            login_response = self.session.post(
                form_data['action'],
                data=login_data,
                headers=login_headers,
                timeout=30,
                impersonate="chrome110",
                allow_redirects=True,
                max_redirects=10
            )

            login_success = False
            # Prüfe, ob das SESSION-Cookie gesetzt wurde
            if hasattr(self.session, 'cookies') and self.session.cookies:
                session_cookie = None
                
                # Versuche, das Cookie aus verschiedenen Cookie-Formaten zu extrahieren
                if hasattr(self.session.cookies, 'get'):
                    session_cookie = self.session.cookies.get('SESSION')
                elif hasattr(self.session.cookies, '__getitem__'):
                    try:
                        session_cookie = self.session.cookies['SESSION']
                    except (KeyError, TypeError):
                        pass
                else:
                    # Iteriere über Cookies, falls es eine Liste/Sammlung ist
                    try:
                        for cookie in self.session.cookies:
                            if hasattr(cookie, 'name') and cookie.name == 'SESSION':
                                session_cookie = cookie.value
                                break
                    except Exception as e:
                        logger.warning(f"Fehler beim Durchsuchen der Cookies: {str(e)}")
                
                if session_cookie:
                    logger.info("SESSION-Cookie gefunden, Login erfolgreich")
                    login_success = True
                else:
                    logger.warning("SESSION-Cookie nicht gefunden, Login möglicherweise nicht erfolgreich")
            else:
                logger.warning("Keine Cookies in der Session gefunden")
                
                    
            if login_success:
                logger.info(f"Login-Anfrage abgeschlossen. Status-Code: {login_response.status_code}")
            else:
                logger.error(f"Login-Anfrage nicht erfolgreich.")
            
            # Wenn der Login erfolgreich war, speichere die Session
            if login_success:
                self.save_session(username)
            
            # Gib die Session und die Response zurück
            return self.session, login_response
            
                
        except Exception as e:
            logger.error(f"Fehler beim Login-Prozess: {str(e)}")
            return self.session, None

# Neue Klasse für Gast-Authentifizierung, die von ControlCenterAuth erbt
class ControlCenterGuestAuth(ControlCenterAuth):
    """
    Authentifizierungsklasse für 1&1 Control Center Gastzugriff
    """
    
    def __init__(self):
        # Rufe den Konstruktor der Elternklasse auf
        super().__init__()
        self.guest_id = None
        
    def create_guest_session(self, guest_url: str) -> Tuple[Any, Any]:
        """
        Erstellt eine Gast-Session durch Aufruf der entsprechenden URLs.
        
        Diese Methode folgt dem Flow:
        1. Extrahiert das Token aus dem Gast-URL
        2. GET zum übergebenen Gast-URL
        3. Folgt den Weiterleitungen bis zur Control-Center-Seite
        
        Args:
            guest_url: Die vollständige URL für den Gastzugriff.
                      Beispiel: "https://www.1und1.de/mc/tsxI7HY4j_IKSCIijcHSZW"
        
        Returns:
            Tuple[Session, bool]: 
                - Die aktive Session
                - True, wenn die Session erfolgreich erstellt wurde, sonst False
        """
        logger.info("Starte Gast-Session-Erstellung mit Verfolgung aller Weiterleitungen")
        
        # Stelle sicher, dass wir eine aktive Session haben
        if not hasattr(self, 'session') or self.session is None:
            self.initialize_session()
        
        # Extrahiere das Token aus der URL
        token_match = re.search(r'/mc/([^/]+)', guest_url)
        if token_match:
            token = token_match.group(1)
            # Verwende das Token als Benutzernamen für die Session
            self.guest_id = f"guest_{token}"
            logger.info(f"Token aus Gast-Link extrahiert: {token}")
        else:
            # Fallback: Generiere eine eindeutige ID für diese Gast-Session
            self.guest_id = f"guest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.warning(f"Kein Token im Gast-Link gefunden, verwende generierte ID: {self.guest_id}")
        
        # Verwende die übergebene URL direkt
        initial_url = guest_url
        logger.info(f"Verwende initialen Gast-Link: {initial_url}")
        
        # Spezifische Headers für diese Anfrage
        headers = {
            "Connection": "keep-alive",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        try:
            # Verwende die Session direkt aus der Klasse
            logger.debug(f"Verwende Session: {id(self.session)}")
            
            # Erste Anfrage an den Gast-Link
            logger.info(f"Sende Anfrage an: {initial_url}")
            response = self.session.get(
                initial_url,
                headers=headers,
                timeout=30,
                impersonate="chrome110",
                allow_redirects=False
            )
            
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get('Location')
                logger.info(f"Weiterleitung zu: {redirect_url}")
                response = self.session.get(
                    redirect_url,
                    headers=headers,
                    timeout=30,
                    impersonate="chrome110",
                    allow_redirects=False
                )

                # Prüfe, ob wir eine Weiterleitung erhalten haben
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get('Location')
                    logger.info(f"Weiterleitung zu: {redirect_url}")

                    # Dritte Anfrage: Folge der Weiterleitung zum Token-URL
                    response = self.session.get(
                        redirect_url,
                        headers=headers,
                        timeout=30,
                        impersonate="chrome110",
                        allow_redirects=False
                    )

                    # Prüfe, ob wir eine weitere Weiterleitung erhalten haben
                    if response.status_code in (301, 302, 303, 307, 308):
                        redirect_url = response.headers.get('Location')
                        logger.info(f"Weiterleitung zu: {redirect_url}")

                        # Vierte Anfrage: Folge der Weiterleitung zur finalen URL
                        response = self.session.get(
                            redirect_url,
                            headers=headers,
                            timeout=30,
                            impersonate="chrome110",
                            allow_redirects=True
                        )

                        # Prüfe, ob wir erfolgreich eine Session erstellt haben
                        if response.status_code == 200:
                            logger.info(f"Gast-Session erfolgreich erstellt mit ID: {self.guest_id}")

                            # Speichere die Session
                            self.save_session(self.guest_id)

                            return self.session, True
            
            logger.error("Konnte keine Gast-Session erstellen")
            return self.session, False
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Gast-Session: {str(e)}")
            return self.session, False
    
    def _create_serializable_session_data(self) -> Dict[str, Any]:
        """
        Erstellt eine serialisierbare Kopie der wichtigen Session-Daten
        
        Returns:
            Dict[str, Any]: Ein Dictionary mit den serialisierbaren Session-Daten
        """
        # Rufe die Methode der Elternklasse auf
        session_data = super()._create_serializable_session_data()
        
        # Füge die Gast-ID hinzu
        session_data["guest_id"] = self.guest_id
        
        return session_data
    
    def _restore_session_from_data(self, session_data: Dict[str, Any]) -> bool:
        """
        Stellt eine Session aus gespeicherten Daten wieder her
        
        Args:
            session_data: Die gespeicherten Session-Daten
            
        Returns:
            bool: True, wenn die Session erfolgreich wiederhergestellt wurde, sonst False
        """
        # Rufe die Methode der Elternklasse auf
        result = super()._restore_session_from_data(session_data)
        
        if result and "guest_id" in session_data:
            self.guest_id = session_data["guest_id"]
            
        return result
    
    def validate_session(self) -> bool:
        """
        Überprüft, ob die aktuelle Gast-Session noch gültig ist
        
        Returns:
            bool: True, wenn die Session gültig ist, sonst False
        """
        if not self.session:
            logger.warning("Keine Session zum Validieren vorhanden")
            return False
            
        try:
            # Gast-Session: Verwende get_guest_contract_id für die Validierung
            from src.api.usability import ConsumptionAPI
            
            # Erstelle ConsumptionAPI-Instanz mit der aktuellen Session
            api = ConsumptionAPI(self.session)
            
            # Versuche, die Gast-Vertrags-ID zu erhalten
            contract_id = api.get_guest_contract_id()
            
            # Wenn eine Vertrags-ID zurückgegeben wurde, ist die Session gültig
            if contract_id:
                logger.info("Gast-Session ist gültig (Vertrags-ID erfolgreich abgerufen)")
                return True
            else:
                logger.warning("Gast-Session ist nicht mehr gültig (keine Vertrags-ID erhalten)")
                return False
                
        except Exception as e:
            logger.error(f"Fehler bei der Session-Validierung: {str(e)}")
            return False
    
    def get_guest_session(self, guest_id: Optional[str] = None, guest_url: Optional[str] = None) -> Tuple[Any, Any]:
        """
        Erstellt eine Gast-Session oder lädt eine bestehende.
        
        Args:
            guest_id: Optional. Die Gast-ID, für die eine Session geladen werden soll.
                     Wenn None, wird eine neue Gast-Session erstellt.
            guest_url: Die vollständige URL für den Gastzugriff.
                      Muss angegeben werden, wenn eine neue Session erstellt werden soll.
            
        Returns:
            Tuple[Any, Any]:
                - Die authentifizierte Session
                - True, wenn die Session erfolgreich erstellt oder geladen wurde, sonst False
        """
        # Wenn eine Gast-URL angegeben wurde, extrahiere das Token für die Gast-ID
        if guest_url and not guest_id:
            token_match = re.search(r'/mc/([^/]+)', guest_url)
            if token_match:
                token = token_match.group(1)
                guest_id = f"guest_{token}"
                logger.info(f"Token aus Gast-Link extrahiert: {token}, verwende als Gast-ID: {guest_id}")
        
        # Wenn eine Gast-ID angegeben wurde, versuche zuerst, eine gespeicherte Session zu laden
        if guest_id and self.load_session(guest_id):
            logger.info(f"Gespeicherte Session für Gast-ID {guest_id} geladen")
            self.guest_id = guest_id
            return self.session, True
        
        # Prüfe, ob eine Gast-URL angegeben wurde
        if not guest_url:
            logger.error("Keine Gast-URL angegeben, kann keine neue Session erstellen")
            return self.session, False
        
        # Erstelle eine neue Gast-Session mit der angegebenen URL
        logger.info("Erstelle neue Gast-Session")
        return self.create_guest_session(guest_url)

if __name__ == "__main__":
    # Dieser Code wird nur ausgeführt, wenn die Datei direkt als Hauptmodul ausgeführt wird
    # und nicht, wenn sie importiert wird
    
    import sys
    
    # Lade Umgebungsvariablen aus .env-Datei
    load_dotenv()
    
    # Prüfe, ob ein Argument übergeben wurde
    if len(sys.argv) > 1 and sys.argv[1] == "guest":
        # Erstelle eine Gast-Session
        auth = ControlCenterGuestAuth()
        
        # Prüfe, ob eine Gast-URL als zweites Argument übergeben wurde
        guest_url = None
        if len(sys.argv) > 2:
            guest_url = sys.argv[2]
            print(f"Verwende übergebenen Gast-Link: {guest_url}")
        else:
            # Versuche, den Gast-Link aus der Umgebungsvariable zu laden
            guest_url = os.getenv("GUEST_URL")
            if guest_url:
                print(f"Verwende Gast-Link aus .env-Datei: {guest_url}")
            else:
                print("Fehler: Kein Gast-Link angegeben und keine GUEST_URL in .env-Datei gefunden")
                print("Verwendung: python -m src.auth.login guest [url]")
                print("  oder setze GUEST_URL in der .env-Datei")
                sys.exit(1)
        
        # Erstelle oder lade eine Gast-Session
        session, success = auth.get_guest_session(guest_url=guest_url)
        
        if success:
            print(f"Gast-Session erfolgreich erstellt mit ID: {auth.guest_id}")
            print(auth.session.cookies)
        else:
            print("Fehler beim Erstellen der Gast-Session")
    else:
        # Normaler Login-Prozess
        # Hier könnte ein interaktiver Login-Prozess implementiert werden
        print("Verwendung: python -m src.auth.login [guest] [url]")
        print("  guest: Erstellt eine Gast-Session")
        print("  url: Optional. Die vollständige URL für den Gastzugriff (z.B. https://www.1und1.de/mc/tsxI7HY4j_)")
        print("  ohne URL-Argument: Verwendet GUEST_URL aus der .env-Datei")
        print("  ohne Argument: Zeigt diese Hilfe an")
