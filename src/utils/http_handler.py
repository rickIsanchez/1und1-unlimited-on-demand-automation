"""
HTTP-Hilfsfunktionen für 1&1 Control Center API Client
"""

import json
import logging
from typing import Dict, Optional, Tuple, Any, List

from curl_cffi import requests
from curl_cffi.requests import Response

from src.config import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

class HttpClient:
    """
    HTTP-Client für 1&1 Control Center API-Anfragen mit curl_cffi
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = DEFAULT_HEADERS.copy()
    
    def update_cookies(self, response: Response) -> None:
        """
        Aktualisiert die Cookies aus der Antwort
        """
        if response.cookies:
            try:
                # Aktualisiere die Session-Cookies direkt
                self.session.cookies.update(response.cookies)
            except Exception as e:
                logger.warning(f"Cookie-Konflikt aufgetreten: {str(e)}")
                # Ignoriere den Fehler
    
    def update_headers(self, headers: Dict[str, str]) -> None:
        """
        Aktualisiert die Headers
        """
        if headers:
            self.headers.update(headers)
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None, 
            allow_redirects: bool = True, follow_redirects: bool = None) -> Response:
        """
        Sendet eine GET-Anfrage
        
        Args:
            url: Die URL für die Anfrage
            params: Query-Parameter
            headers: HTTP-Headers
            allow_redirects: Ob Weiterleitungen automatisch verfolgt werden sollen
            follow_redirects: Veraltet, verwende allow_redirects
            
        Returns:
            Response: Die HTTP-Antwort
        """
        # Für Abwärtskompatibilität
        if follow_redirects is not None:
            allow_redirects = follow_redirects
            logger.warning("Der Parameter 'follow_redirects' ist veraltet. Bitte verwende 'allow_redirects'.")
        
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        logger.debug(f"GET-Anfrage an {url}")
        response = self.session.get(
            url,
            params=params,
            headers=request_headers,
            timeout=REQUEST_TIMEOUT,
            impersonate="chrome110",
            allow_redirects=allow_redirects
        )
        
        self.update_cookies(response)
        return response
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, 
             json_data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None, 
             allow_redirects: bool = True, follow_redirects: bool = None) -> Response:
        """
        Sendet eine POST-Anfrage
        
        Args:
            url: Die URL für die Anfrage
            data: Formulardaten
            json_data: JSON-Daten
            headers: HTTP-Headers
            allow_redirects: Ob Weiterleitungen automatisch verfolgt werden sollen
            follow_redirects: Veraltet, verwende allow_redirects
            
        Returns:
            Response: Die HTTP-Antwort
        """
        # Für Abwärtskompatibilität
        if follow_redirects is not None:
            allow_redirects = follow_redirects
            logger.warning("Der Parameter 'follow_redirects' ist veraltet. Bitte verwende 'allow_redirects'.")
        
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        logger.debug(f"POST-Anfrage an {url}")
        response = self.session.post(
            url,
            data=data,
            json=json_data,
            headers=request_headers,
            timeout=REQUEST_TIMEOUT,
            impersonate="chrome110",
            allow_redirects=allow_redirects
        )
        
        self.update_cookies(response)
        return response
    
    def extract_form_data(self, html_content: str) -> Dict[str, str]:
        """
        Extrahiert Formularfelder aus HTML-Inhalt
        Einfache Implementierung, die für komplexere Fälle erweitert werden kann
        """
        import re
        
        form_data = {}
        
        # Suche nach input-Feldern
        input_pattern = r'<input[^>]*name=["\']([^"\']*)["\'][^>]*value=["\']([^"\']*)["\']'
        inputs = re.findall(input_pattern, html_content)
        
        for name, value in inputs:
            form_data[name] = value
        
        return form_data 