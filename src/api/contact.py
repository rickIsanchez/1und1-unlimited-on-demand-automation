"""
API-Funktionen für 1&1 Control Center - Kontaktfunktionen
"""
from typing import Dict, Any
import re
import random
from curl_cffi import requests
from src.utils.logger import setup_logger
from src.utils.load_proxies import load_proxies

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

def normalize_phone_number(phone_number: str) -> str:
    """
    Normalisiert verschiedene Telefonformate in das Format "004915562680861"
    
    Args:
        phone_number (str): Die zu normalisierende Telefonnummer
        
    Returns:
        str: Die normalisierte Telefonnummer im Format "004915562680861"
    """
    # Entferne alle Leerzeichen, Bindestriche und andere Sonderzeichen
    cleaned_number = re.sub(r'[\s\-\(\)\/\.]', '', phone_number)
    
    # Wenn die Nummer mit + beginnt, ersetze + durch 00
    if cleaned_number.startswith('+'):
        cleaned_number = '00' + cleaned_number[1:]
    
    # Wenn die Nummer mit 0 beginnt und nicht mit 00, füge deutsche Ländervorwahl hinzu
    if cleaned_number.startswith('0') and not cleaned_number.startswith('00'):
        cleaned_number = '0049' + cleaned_number[1:]
    
    # Wenn die Nummer weder mit + noch mit 0 beginnt, füge deutsche Ländervorwahl hinzu
    if not cleaned_number.startswith('00') and not cleaned_number.startswith('+'):
        # Prüfe, ob es sich um eine deutsche Handynummer ohne Vorwahl handelt (beginnt mit 15, 16, 17)
        if re.match(r'^1[5-7]', cleaned_number):
            cleaned_number = '0049' + cleaned_number
    
    return cleaned_number

class ContactAPI:
    """
    API-Klasse für Kontaktfunktionen im 1&1 Control Center
    """
    
    def __init__(self):
        """
        Initialisiert die ContactAPI-Klasse
        """
        self.base_url = 'https://www.1und1.de'
        self.current_proxy = None
        
    def send_phone_number_token(self, phone_number: str) -> Dict[str, Any]:
        """
        Sendet eine Anfrage zum Versenden eines Tokens an die angegebene Telefonnummer
        
        Args:
            phone_number (str): Die Telefonnummer, an die der Token gesendet werden soll
            
        Returns:
            Dict[str, Any]: Die Antwort des Servers als Dictionary
        """
        # Normalisiere die Telefonnummer
        normalized_phone_number = normalize_phone_number(phone_number)
        logger.info(f"Normalisierte Telefonnummer: {normalized_phone_number} (Original: {phone_number})")
        
        url = f"{self.base_url}/frontend/contact/mc-token-send-phone-number"
        print(url)
        
        headers = {
            "Host": "www.1und1.de",
            "Connection": "keep-alive",
            "sec-ch-ua-platform": "\"macOS\"",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "Content-Type": "application/json",
            "sec-ch-ua-mobile": "?0",
            "Origin": "https://www.1und1.de",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.1und1.de/mobile-center-no-mobile-data",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "ADRUM": "isAjax:true"
        }
        
        payload = {
            "phoneNumber": normalized_phone_number
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Wähle einen neuen Proxy, wenn noch keiner gesetzt ist oder der vorherige fehlgeschlagen ist
                if not self.current_proxy:
                    self.current_proxy = get_random_proxy()
                    logger.info(f"Verwende Proxy: {self.current_proxy}")
                
                response = requests.post(
                    url=url,
                    headers=headers,
                    json=payload,
                    impersonate="chrome110",
                    proxies=self.current_proxy
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": 'Mobile Center Token erfolgreich angefragt für ' + phone_number
                    }
                else:
                    logger.error(f"Fehler beim Anfragen des Mobile Center Tokens: {response.status_code} - {response.text}")
                    # Bei einem Fehler den aktuellen Proxy zurücksetzen und einen neuen versuchen
                    self.current_proxy = None
                    retry_count += 1
                    continue
                    
            except Exception as e:
                logger.error(f"Ausnahme beim Anfragen des Mobile Center Tokens: {str(e)}")
                # Bei einer Ausnahme den aktuellen Proxy zurücksetzen und einen neuen versuchen
                self.current_proxy = None
                retry_count += 1
                continue
        
        return {
            "success": False,
            "error": "Maximale Anzahl an Versuchen erreicht",
            "message": "Konnte keine erfolgreiche Verbindung herstellen"
        }