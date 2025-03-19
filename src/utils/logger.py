"""
Logger-Utility für 1&1 Control Center API Client
Bietet einheitliches Logging-Format mit optionaler Farbunterstützung
"""

import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Union, Literal, Dict, Any

# Versuche, die Konfiguration zu importieren
try:
    from src.config import LOGGER_USE_COLORS
except ImportError:
    # Fallback, wenn die Konfiguration nicht importiert werden kann
    LOGGER_USE_COLORS = False

# ANSI-Farbcodes
COLORS = {
    "RESET": "\033[0m",
    "BLACK": "\033[30m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}

# Farben für verschiedene Log-Level
LEVEL_COLORS = {
    logging.DEBUG: COLORS["BLUE"],
    logging.INFO: COLORS["GREEN"],
    logging.WARNING: COLORS["YELLOW"],
    logging.ERROR: COLORS["RED"],
    logging.CRITICAL: COLORS["BOLD"] + COLORS["RED"],
}

# Standard-Logs-Verzeichnis
DEFAULT_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")

# Standardmäßig Farben entsprechend der Konfiguration verwenden
USE_COLORS = LOGGER_USE_COLORS

class ColoredFormatter(logging.Formatter):
    """Formatter für farbige Log-Ausgaben"""
    
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=USE_COLORS):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors
    
    def format(self, record):
        if not self.use_colors:
            return super().format(record)
            
        levelname = record.levelname
        levelno = record.levelno
        
        # Farbigen Levelname erstellen
        colored_levelname = f"{LEVEL_COLORS.get(levelno, COLORS['RESET'])}{levelname}{COLORS['RESET']}"
        
        # Original-Levelname temporär ersetzen
        record.levelname = colored_levelname
        result = super().format(record)
        
        # Original-Levelname wiederherstellen
        record.levelname = levelname
        
        return result

def setup_logger(
    name: str,
    level: Union[int, str] = logging.INFO,
    format_string: Optional[str] = None,
    log_to_file: bool = True,
    log_file: Optional[str] = None,
    log_retention_hours: int = 12,
    use_colors: bool = USE_COLORS,
) -> logging.Logger:
    """
    Erstellt und konfiguriert einen Logger mit einheitlichem Format und optionaler Farbunterstützung.
    
    Args:
        name: Name des Loggers
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Optionales Format-String für den Logger
        log_to_file: Ob in eine Datei geloggt werden soll (Standard: True)
        log_file: Optionaler Dateipfad für die Protokollierung in eine Datei
                 (Standard: logs/{name}_{datum}.log)
        log_retention_hours: Anzahl der Stunden, für die Logs aufbewahrt werden sollen (Standard: 12)
        use_colors: Ob Farbausgabe verwendet werden soll (Standard: False)
        
    Returns:
        Konfigurierter Logger
    """
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Alle vorhandenen Handler entfernen
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console-Handler mit optionaler Farbunterstützung
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(format_string, use_colors=use_colors))
    logger.addHandler(console_handler)
    
    # Optional: Datei-Handler ohne Farben
    if log_to_file:
        # Logs-Verzeichnis erstellen, falls es nicht existiert
        logs_dir = os.path.dirname(log_file) if log_file else DEFAULT_LOGS_DIR
        os.makedirs(logs_dir, exist_ok=True)
        
        # Bestimme die Aufbewahrungsdauer basierend auf dem Logger-Namen
        retention_hours = log_retention_hours
        
        # Spezielle Behandlung für usability.py und login.py
        if name == "src.api.usability" or name == "src.auth.login":
            retention_hours = 48  # 48 Stunden Aufbewahrung für diese Module
            
            # Logdatei-Pfad für diese speziellen Module
            module_name = name.split('.')[-1]
            log_file = os.path.join(logs_dir, f"{module_name}.log")
            
            # Eigener File-Handler für diese Module
            module_file_handler = TimedRotatingFileHandler(
                log_file,
                when='H',
                interval=1,
                backupCount=retention_hours
            )
            module_file_handler.setFormatter(logging.Formatter(format_string))
            logger.addHandler(module_file_handler)
            
            logger.info(f"Logs für {name} werden in {log_file} gespeichert (Aufbewahrung: {retention_hours} Stunden)")
        
        # Zentrales Log-File für alle Logs
        central_log_file = os.path.join(logs_dir, "control_center.log")
        central_file_handler = TimedRotatingFileHandler(
            central_log_file,
            when='H',
            interval=1,
            backupCount=12  # 12 Stunden Aufbewahrung für das zentrale Log
        )
        central_file_handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(central_file_handler)
        
        logger.info(f"Logs werden zentral in {central_log_file} gespeichert (Aufbewahrung: 12 Stunden)")
    
    return logger

# Vordefinierte Logger-Instanz für einfachen Import
default_logger = setup_logger("1und1_control_center", use_colors=USE_COLORS)

# Hilfsfunktionen für einfachen Zugriff
def get_logger(name: str, **kwargs) -> logging.Logger:
    """Gibt einen konfigurierten Logger mit dem angegebenen Namen zurück"""
    return setup_logger(name, **kwargs)

def debug(msg: str, *args, **kwargs) -> None:
    """Debug-Log über den Standard-Logger"""
    default_logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs) -> None:
    """Info-Log über den Standard-Logger"""
    default_logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs) -> None:
    """Warning-Log über den Standard-Logger"""
    default_logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs) -> None:
    """Error-Log über den Standard-Logger"""
    default_logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs) -> None:
    """Critical-Log über den Standard-Logger"""
    default_logger.critical(msg, *args, **kwargs) 