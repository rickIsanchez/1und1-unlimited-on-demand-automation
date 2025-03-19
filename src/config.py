"""
Konfigurationseinstellungen für 1&1 Control Center API Client
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Versuche, python-dotenv zu importieren
try:
    from dotenv import load_dotenv
    # Lade .env-Datei, falls vorhanden
    env_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    dotenv_loaded = True
except ImportError:
    dotenv_loaded = False
    print("Hinweis: python-dotenv ist nicht installiert. Umgebungsvariablen werden nur aus der Systemumgebung geladen.")

# Logger konfigurieren
logger = logging.getLogger(__name__)

# URLs
API_KEY_WEBSHARE = os.getenv("API_KEY_WEBSHARE", "")
USE_WEBSHARE=os.getenv("USE_WEBSHARE", "false")

BASE_URL = "https://control-center.1und1.de"
LOGIN_URL = f"{BASE_URL}/login"
AUTH_URL = f"{BASE_URL}/auth"

# HTTP Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
}

# Timeouts
REQUEST_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # Sekunden

# Monitor-Einstellungen
MONITOR_THRESHOLD_GB = float(os.getenv("MONITOR_THRESHOLD_GB", "1.0"))
MONITOR_CHECK_INTERVAL_SECONDS = int(os.getenv("MONITOR_CHECK_INTERVAL_SECONDS", "60"))
MONITOR_FAST_CHECK_INTERVAL_SECONDS = int(os.getenv("MONITOR_FAST_CHECK_INTERVAL_SECONDS", "5"))
MONITOR_LOG_RETENTION_HOURS = int(os.getenv("MONITOR_LOG_RETENTION_HOURS", "12"))

# Logger-Einstellungen
LOGGER_USE_COLORS = os.getenv("LOGGER_USE_COLORS", "false").lower() in ("true", "1", "yes")

# Anmeldedaten aus Umgebungsvariablen
USERNAME = os.getenv("CONTROL_CENTER_USERNAME", "")
PASSWORD = os.getenv("CONTROL_CENTER_PASSWORD", "")
# Gast-Link aus Umgebungsvariablen
GUEST_URL = os.getenv("GUEST_URL", "")

# Vertrags-IDs aus Umgebungsvariablen
CONTRACT_IDS_STR = os.getenv("CONTROL_CENTER_CONTRACT_IDS", "")
CONTRACT_IDS = [id.strip() for id in CONTRACT_IDS_STR.split(",")] if CONTRACT_IDS_STR else []

def get_credentials() -> Dict[str, str]:
    """
    Gibt die Anmeldedaten aus den Umgebungsvariablen zurück
    
    Returns:
        Dict[str, str]: Ein Dictionary mit Benutzername, Passwort und optional Gast-Link
    """
    credentials = {
        "username": USERNAME,
        "password": PASSWORD,
        "guest_url": GUEST_URL
    }
    
    # Prüfe, ob entweder Anmeldedaten oder Gast-Link vorhanden sind
    if not GUEST_URL and (not USERNAME or not PASSWORD):
        logger.warning("Weder vollständige Anmeldedaten noch Gast-Link in Umgebungsvariablen gefunden. Bitte .env-Datei konfigurieren.")
    
    return credentials

def get_contract_ids() -> List[str]:
    """
    Gibt die Vertrags-IDs aus den Umgebungsvariablen zurück
    
    Returns:
        List[str]: Eine Liste mit Vertrags-IDs
    """
    if not CONTRACT_IDS:
        logger.warning("Keine Vertrags-IDs in Umgebungsvariablen gefunden. Bitte .env-Datei konfigurieren.")
    
    return CONTRACT_IDS

def get_primary_contract_id() -> Optional[str]:
    """
    Gibt die erste Vertrags-ID aus den Umgebungsvariablen zurück
    
    Returns:
        Optional[str]: Die erste Vertrags-ID oder None, wenn keine vorhanden
    """
    contract_ids = get_contract_ids()
    return contract_ids[0] if contract_ids else None 