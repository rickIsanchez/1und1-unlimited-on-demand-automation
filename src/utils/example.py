"""
Beispiel für die Verwendung des Loggers in verschiedenen Szenarien
"""

# Methode 1: Direkter Import der Hilfsfunktionen
from src.utils.logger import debug, info, warning, error, critical

# Methode 2: Import des setup_logger und Erstellung eines eigenen Loggers
from src.utils.logger import setup_logger

# Methode 3: Import über das utils-Paket
from src.utils import debug as utils_debug, info as utils_info

# Beispiel für die Verwendung der direkten Hilfsfunktionen
def beispiel_direkte_funktionen():
    debug("Dies ist eine Debug-Nachricht")
    info("Dies ist eine Info-Nachricht")
    warning("Dies ist eine Warnung")
    error("Dies ist ein Fehler")
    critical("Dies ist ein kritischer Fehler")

# Beispiel für die Verwendung eines eigenen Loggers
def beispiel_eigener_logger():
    # Logger mit eigenem Namen erstellen
    logger = setup_logger("mein_modul")
    
    # Logger mit angepasstem Format erstellen
    custom_logger = setup_logger(
        "custom_format",
        format_string="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Logger mit Datei-Ausgabe erstellen
    file_logger = setup_logger(
        "file_logger",
        log_to_file="logs/example.log"
    )
    
    # Verwendung der Logger
    logger.debug("Debug-Nachricht vom eigenen Logger")
    logger.info("Info-Nachricht vom eigenen Logger")
    
    custom_logger.warning("Warnung vom angepassten Logger")
    
    file_logger.error("Fehler, der in die Datei geschrieben wird")
    file_logger.info("Info, die in die Datei geschrieben wird")

# Beispiel für die Verwendung über das utils-Paket
def beispiel_utils_import():
    utils_debug("Debug über utils-Import")
    utils_info("Info über utils-Import")

if __name__ == "__main__":
    info("Starte Beispiele für Logger-Verwendung")
    
    beispiel_direkte_funktionen()
    beispiel_eigener_logger()
    beispiel_utils_import()
    
    info("Beispiele abgeschlossen") 