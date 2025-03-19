#!/usr/bin/env python3
"""
Skript zur Überwachung des Datenverbrauchs für den Vertrag 123456789.
Prüft regelmäßig den Datenverbrauch und erhöht automatisch das Highspeed-Volumen,
wenn weniger als der konfigurierte Schwellenwert verbleibt.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

from src.utils.monitor import monitor_data_usage
from src.utils.logger import setup_logger

# Logger für dieses Modul konfigurieren
logger = setup_logger(
    name="monitor_vertrag",
    level="INFO",
    log_to_file=True,
    log_retention_hours=12
)

def main():
    """
    Hauptfunktion zum Starten der Datenüberwachung.
    """
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description="Überwacht den Datenverbrauch eines 1&1-Vertrags")
    parser.add_argument("--username", help="Benutzername für die Anmeldung")
    parser.add_argument("--password", help="Passwort für die Anmeldung")
    parser.add_argument("--guest-url", help="Gast-Link für den Zugriff ohne Anmeldedaten")
    parser.add_argument("--contract-id", help="Vertrags-ID, die überwacht werden soll")
    parser.add_argument("--threshold", type=float, help="Schwellenwert in GB, bei dem das Highspeed-Volumen erhöht wird")
    parser.add_argument("--interval", type=int, help="Prüfintervall in Sekunden")
    parser.add_argument("--fast-interval", type=int, help="Schnelleres Prüfintervall in Sekunden, wenn der Schwellenwert unterschritten wird")
    parser.add_argument("--max-interval", type=int, help="Maximales Prüfintervall in Sekunden (Standard: 300 = 5 Minuten)")
    parser.add_argument("--initial-interval", type=int, help="Initiales Intervall in Sekunden für die dynamische Berechnung (Standard: 60 = 1 Minute)")
    parser.add_argument("--dynamic", action="store_true", help="Dynamische Intervallberechnung aktivieren")
    parser.add_argument("--no-dynamic", action="store_false", dest="dynamic", help="Dynamische Intervallberechnung deaktivieren")
    parser.add_argument("--log-retention", type=int, default=12, help="Anzahl der Stunden, für die Logs aufbewahrt werden sollen (Standard: 12)")
    args = parser.parse_args()
    
    # Umgebungsvariablen laden
    load_dotenv()
    
    logger.info("=== 1&1 Datenverbrauch-Monitor gestartet ===")
    logger.info(f"Log-Aufbewahrung: {args.log_retention} Stunden")
    
    try:
        # Überwachung starten mit Parametern aus Kommandozeilenargumenten oder .env-Datei
        monitor = monitor_data_usage(
            contract_id=args.contract_id,
            username=args.username,
            password=args.password,
            guest_url=args.guest_url,
            threshold_gb=args.threshold,
            check_interval_seconds=args.interval,
            fast_check_interval_seconds=args.fast_interval,
            max_check_interval_seconds=args.max_interval,
            dynamic_interval=args.dynamic,
            initial_dynamic_interval_seconds=args.initial_interval,
            log_retention_hours=args.log_retention
        )
        
        if monitor is None:
            logger.error("Konnte Monitor nicht starten. Bitte überprüfen Sie die Konfiguration.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Überwachung durch Benutzer unterbrochen")
    except Exception as e:
        logger.error(f"Fehler beim Starten der Überwachung: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 