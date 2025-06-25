# 1&1 Control Center API Client

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Ein leistungsstarker, modularer Python-Client für die Interaktion mit dem 1&1 Control Center. Diese inoffizielle API ermöglicht es Ihnen, Ihre 1&1 Mobilfunkverträge zu verwalten, Verbrauchsdaten abzurufen und verschiedene Aktionen automatisiert durchzuführen.

## 🚀 Funktionen

- **Automatisierte Authentifizierung** - Sichere Anmeldung beim 1&1 Control Center mit Sitzungsverwaltung
- **Verbrauchsdaten** - Abrufen von Datenvolumen, Telefoniezeiten und SMS-Nutzung
- **Highspeed-Volumen** - Automatisierte Buchung von zusätzlichem Datenvolumen
- **Sitzungspersistenz** - Speichern und Wiederverwenden von Sitzungen für schnellere Anfragen
- **Fehlerbehandlung** - Robuste Fehlerbehandlung mit automatischer Wiederanmeldung
- **Modulare Architektur** - Einfach erweiterbar für zusätzliche Funktionen
- **Datenüberwachung** - Automatische Überwachung des Datenverbrauchs mit konfigurierbaren Schwellenwerten
- **Automatisches Logging** - Speicherung von Logs mit konfigurierbarer Aufbewahrungsdauer

## 📋 Voraussetzungen

- Python 3.8 oder höher
- pip (Python-Paketmanager)
- 1&1 Mobilfunkvertrag mit Zugang zum Control Center

## 🔧 Installation


1. **Repository herunterladen**
   ```bash
   git clone https://github.com/rickIsanchez/1und1-unlimited-on-demand-automation.git
   cd 1und1-unlimited-on-demand-automation
   ```

2. **Virtuelle Python-Umgebung einrichten** (isoliert die Abhängigkeiten)
   ```bash
   # Umgebung erstellen
   python -m venv .venv
   
   # Umgebung aktivieren
   # Unter Windows:
   .venv\Scripts\activate
   
   # Unter macOS/Linux:
   source .venv/bin/activate
   ```

3. **Benötigte Bibliotheken installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurationsdatei vorbereiten**
   ```bash
   # Beispielkonfiguration kopieren
   cp .env.example .env
   
   # Datei mit einem Texteditor öffnen und anpassen
   # z.B. mit VS Code:
   code .env
   # oder mit Notepad (Windows):
   notepad .env
   # oder mit nano (Linux/macOS):
   nano .env
   ```

5. **Starten**
   ```bash
   # Hauptprogramm mit der Überwachung starten (automatische Highspeed-Volumen-Buchung)
   python main.py
   
   # Bei Problemen mit Berechtigungen
   chmod +x main.py
   ./main.py
   ```

## ⚙️ Konfiguration der .env-Datei

Die `.env`-Datei enthält alle wichtigen Einstellungen für das Programm. Hier eine detaillierte Erklärung aller Konfigurationsoptionen:

```
# Anmeldedaten für das 1&1 Control Center (entweder Benutzername und Passwort ODER Gast-Link verwenden)
CONTROL_CENTER_USERNAME=ihre-email@beispiel.de    # Ihre 1&1-Zugangsdaten (E-Mail)
CONTROL_CENTER_PASSWORD=ihr-passwort              # Ihr 1&1-Passwort

# Alternativ: Gast-Link für den Zugriff ohne Anmeldedaten
# Beispiel: https://www.1und1.de/mc/tsxI7HY4j_...
# Diese Links werden automatisch per SMS gesendet, wenn Sie 80% Ihres Datenvolumens erreichen
# Hinweis: Gast-Links sind zeitlich begrenzt und laufen nach einigen Tagen/Wochen ab, sofern nicht in Verwendung!
GUEST_URL=

# Vertrags-ID(s) - finden Sie im Control Center unter "Meine Produkte"
CONTROL_CENTER_CONTRACT_IDS=123456789             # Ihre Vertragsnummer 
# Mehrere Verträge können mit Komma getrennt werden, z.B.: 123456789,987654321

# API-Einstellungen
API_TIMEOUT=30                                   # Timeout in Sekunden für API-Anfragen

# Monitor-Einstellungen
# Schwellenwert in GB, bei dem zusätzliches Datenvolumen gebucht wird
MONITOR_THRESHOLD_GB=1.0                         # Wenn weniger als 1 GB verfügbar ist, wird neues Volumen gebucht

# Prüfintervalle für die Überwachung
MONITOR_CHECK_INTERVAL_SECONDS=60                # Normales Prüfintervall (1 Minute)
MONITOR_FAST_CHECK_INTERVAL_SECONDS=5            # Schnelleres Intervall wenn der Schwellenwert fast erreicht ist
MONITOR_MAX_CHECK_INTERVAL_SECONDS=300           # Maximales Prüfintervall (5 Minuten)
MONITOR_INITIAL_DYNAMIC_INTERVAL_SECONDS=60      # Initiales Intervall für die dynamische Berechnung

# Dynamische Intervallberechnung
MONITOR_DYNAMIC_INTERVAL=true                    # true: Intervalle dynamisch anpassen, false: feste Intervalle

# Logging-Einstellungen
MONITOR_LOG_RETENTION_HOURS=12                   # Log-Dateien werden nach dieser Zeit automatisch gelöscht
MONITOR_LOG_LEVEL=INFO                           # Log-Level: DEBUG, INFO, WARNING, ERROR oder CRITICAL
LOGGER_USE_COLORS=false                          # Farbige Logs aktivieren/deaktivieren (für bessere Kompatibilität 
                                                 # mit Ubuntu Cockpit auf false setzen)
```

### Tipps zur Konfiguration:

- **Authentifizierung**: Sie haben zwei Möglichkeiten:
  - Standard-Login mit Benutzername und Passwort
  - Gast-Link für den Zugriff ohne Anmeldedaten (sicherer, da keine Passwörter gespeichert werden)
- **Schwellenwert**: Wählen Sie einen Wert, der zu Ihrem Nutzungsverhalten passt. Für intensive Nutzer empfehlen wir 1-2 GB.
- **Prüfintervalle**: 
  - Bei niedriger Datennutzung können längere Intervalle (z.B. 120-300 Sekunden) ausreichen.
  - Bei hoher Datennutzung sollten kürzere Intervalle (30-60 Sekunden) verwendet werden.
- **Dynamische Intervalle**: Diese Funktion passt das Prüfintervall automatisch basierend auf der aktuellen Datenverbrauchsrate an:
  - Bei hohem Verbrauch werden Überprüfungen häufiger durchgeführt
  - Bei niedrigem Verbrauch werden Überprüfungen in größeren Abständen durchgeführt
- **API-Timeout**: Bei instabiler Internetverbindung kann ein höherer Wert sinnvoll sein.
- **Log-Einstellungen**: 
  - Bei Debugging-Problemen empfiehlt es sich, die Aufbewahrungsdauer zu erhöhen (z.B. auf 24-48 Stunden)
  - Deaktivieren Sie farbige Logs für bessere Kompatibilität mit bestimmten Systemen wie Ubuntu Cockpit

### 🔐 Gast-Link-Authentifizierung - Detaillierte Anleitung

Die Gast-Link-Authentifizierung ist das **sicherere Verfahren**, da keine Passwörter in der Konfigurationsdatei gespeichert werden müssen. Hier die vollständige Anleitung:

#### Wie erhalten Sie einen Gast-Link?

1. **Automatisch per SMS**: 1&1 sendet automatisch Gast-Links per SMS, wenn Sie 80% Ihres Datenvolumens erreichen
2. **Link-Format**: Der Link hat die Form `https://www.1und1.de/mc/EINDEUTIGES_TOKEN`
3. **Beispiel-SMS**: "Ihr Datenvolumen ist zu 80% aufgebraucht. Hier können Sie zusätzliches Volumen buchen: https://www.1und1.de/mc/EINDEUTIGES_TOKEN"

#### Gast-Link in der .env-Datei konfigurieren:

```env
# Gast-Link aus der SMS von 1&1 eintragen
GUEST_URL=https://www.1und1.de/mc/EINDEUTIGES_TOKEN

# Standard-Anmeldedaten leer lassen, wenn Gast-Link verwendet wird
CONTROL_CENTER_USERNAME=
CONTROL_CENTER_PASSWORD=
```

#### ⚠️ Wichtige Hinweise zu Gast-Links:

- **Zeitlich begrenzt**: Gast-Links laufen nach einigen Tagen bis Wochen ab
- **Nicht garantiert**: 1&1 sendet nicht immer automatisch SMS-Links
- **Automatische Erneuerung**: Bei abgelaufenen Links müssen Sie warten, bis ein neuer Link per SMS gesendet wird

#### Mit Benutzername und Passwort:

```python
from src.auth.login import ControlCenterAuth
from src.api.usability import ConsumptionAPI

# Authentifizierung
auth = ControlCenterAuth()
session, login_success = auth.login("ihre-email@beispiel.de", "ihr-passwort")

if login_success:
    # Verbrauchsdaten abrufen
    api = ConsumptionAPI(session)
    contract_id = "IHR_VERTRAGS_ID"  # oder aus config.py abrufen
    
    # Zusammenfassung der Verbrauchsdaten
    summary = api.get_consumption_summary(contract_id)
    print(f"Datenvolumen: {summary['datenvolumen']['verbraucht']} von {summary['datenvolumen']['gesamt']}")
    print(f"Telefonie: {summary['telefonie']['verbraucht']} von {summary['telefonie']['gesamt']}")
    print(f"SMS: {summary['sms']['verbraucht']} von {summary['sms']['gesamt']}")
```

### Verwendung über die Kommandozeile

```bash
# Mit Anmeldedaten aus .env-Datei
python main.py

# Mit expliziter Angabe des Benutzernamens
python main.py --username ihre-email@beispiel.de
```

### Highspeed-Volumen erhöhen

```python
from src.api.usability import ConsumptionAPI

api = ConsumptionAPI()
api.set_session(username="ihre-email@beispiel.de", password="ihr-passwort")

contract_id = "IHR_VERTRAGS_ID"
result = api.increase_highspeed_volume(contract_id)

if result["erfolg"]:
    print(f"Erfolg: {result['nachricht']}")
else:
    print(f"Fehler: {result['nachricht']}")
```

### Automatische Datenüberwachung

Das Projekt bietet eine Funktion zur automatischen Überwachung des Datenverbrauchs. Wenn das verbleibende Highspeed-Volumen unter einen konfigurierbaren Schwellenwert fällt, wird automatisch zusätzliches Volumen gebucht.

#### Verwendung des Monitor-Skripts

```bash
# Überwachung mit Einstellungen aus der .env-Datei starten
python monitor_vertrag.py

# Mit expliziten Parametern
python monitor_vertrag.py --username ihre-email@beispiel.de --password ihr-passwort --threshold 0.5 --interval 60 --fast-interval 5 --contract-id 123456789 --log-retention 24
```

#### Programmgesteuerte Verwendung

```python
from src.utils.monitor import monitor_data_usage

# Überwachung mit Einstellungen aus der .env-Datei starten
monitor = monitor_data_usage()

# Oder mit expliziten Parametern
monitor = monitor_data_usage(
    contract_id="IHR_VERTRAGS_ID",
    username="ihre-email@beispiel.de",
    password="ihr-passwort",
    threshold_gb=1.0,                # Schwellenwert in GB
    check_interval_seconds=60,       # Prüfintervall in Sekunden
    fast_check_interval_seconds=5,   # Schnelleres Prüfintervall in Sekunden
    log_retention_hours=12           # Log-Aufbewahrung in Stunden
)

# Die Funktion blockiert und führt die Überwachung durch, bis sie unterbrochen wird
```

### Logging-Funktionalität

Das Projekt verwendet ein automatisches Logging-System, das Informationen sowohl in der Konsole als auch in Logdateien speichert. Die Logs werden im `logs`-Verzeichnis gespeichert und automatisch rotiert, sodass nur die Logs der letzten konfigurierten Stunden (standardmäßig 12 Stunden) aufbewahrt werden.

```python
from src.utils.logger import setup_logger

# Logger mit benutzerdefinierten Einstellungen erstellen
logger = setup_logger(
    name="mein_logger",
    level="INFO",                  # Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_to_file=True,              # In Datei loggen
    log_retention_hours=12         # Aufbewahrungsdauer in Stunden
)

# Logger verwenden
logger.info("Dies ist eine Info-Nachricht")
logger.warning("Dies ist eine Warnung")
logger.error("Dies ist ein Fehler")
```

## 📁 Projektstruktur

```
1und1-control-center/
├── .env                  # Lokale Konfiguration (nicht im Repository)
├── .env.example          # Beispiel für Konfigurationsdatei
├── .gitignore            # Git-Ignorierungsdatei
├── README.md             # Diese Datei
├── logs/                 # Verzeichnis für Logdateien (automatisch erstellt)
├── main.py               # Haupteinstiegspunkt
├── monitor_vertrag.py    # Skript zur Datenüberwachung
├── requirements.txt      # Python-Abhängigkeiten
└── src/                  # Quellcode
    ├── __init__.py
    ├── config.py         # Konfigurationsmanagement
    ├── api/              # API-Endpunkte
    │   ├── __init__.py
    │   └── usability.py  # Verbrauchsdaten-API
    ├── auth/             # Authentifizierungsmodule
    │   ├── __init__.py
    │   └── login.py      # Login-Funktionalität
    └── utils/            # Hilfsfunktionen
        ├── __init__.py
        ├── logger.py     # Logging-Funktionalität
        └── monitor.py    # Datenüberwachungsfunktionalität
```

## 🛠️ Erweiterung

Das Projekt ist modular aufgebaut und kann leicht erweitert werden:

1. **Neue API-Endpunkte hinzufügen**
   - Erstellen Sie eine neue Datei in `src/api/` für den spezifischen Endpunkt
   - Implementieren Sie eine Klasse, die die Basislogik aus `ConsumptionAPI` wiederverwendet

2. **Authentifizierungsmethoden erweitern**
   - Erweitern Sie die `ControlCenterAuth`-Klasse in `src/auth/login.py`

3. **Hilfsfunktionen hinzufügen**
   - Fügen Sie neue Module im `src/utils/`-Verzeichnis hinzu

4. **Überwachungsfunktionen anpassen**
   - Erweitern Sie die `DataMonitor`-Klasse in `src/utils/monitor.py` für zusätzliche Überwachungsfunktionen

## ⚠️ Wichtige Hinweise

### ❗ Haftungsausschluss und Nutzungsbedingungen

- **Dieses Projekt ist ein experimentelles Hobby-Projekt**, das aus Interesse, zum Testen und aus Spaß an der Programmierung entwickelt wurde.
- **NICHT für den produktiven Einsatz gedacht**: Die Nutzung erfolgt vollständig auf eigene Gefahr und Verantwortung.
- **Keine offizielle Unterstützung**: Dieses Projekt ist in keiner Weise von 1&1 unterstützt, genehmigt oder autorisiert.
- **Verstoß gegen AGB möglich**: Laut den Allgemeinen Geschäftsbedingungen (AGB) von 1&1 ist die Verwendung von Skripten und Bots zur Interaktion mit deren Diensten **nicht gestattet**. Die Nutzung dieses Tools könnte einen Verstoß gegen diese Bedingungen darstellen.
- **Mögliche Konsequenzen**:
  - Temporäre oder permanente Sperrung Ihres 1&1-Kontos
  - Zusätzliche Kosten durch automatisierte Buchungen von Datenvolumen
  - Einschränkungen bei der Nutzung von 1&1-Diensten
  - Rechtliche Folgen bei Verstoß gegen die Nutzungsbedingungen

- Überprüfen Sie regelmäßig die aktuellen AGB von 1&1, ob sich Bedingungen geändert haben

**HINWEIS:** Der Autor übernimmt keine Haftung für jegliche Schäden oder Verluste, die durch die Nutzung dieser Software entstehen könnten. **BENUTZEN AUF EIGENE GEFAHR!**

## 🐛 Fehlerbehebung

- **Authentifizierungsfehler**: Stellen Sie sicher, dass Ihre Anmeldedaten korrekt sind und Sie Zugriff auf das 1&1 Control Center haben.
- **Session-Fehler**: Löschen Sie gespeicherte Sitzungsdateien und versuchen Sie es erneut.
- **Netzwerkfehler**: Überprüfen Sie Ihre Internetverbindung und ob die 1&1-Server erreichbar sind.
- **Überwachungsprobleme**: Überprüfen Sie die Logs auf Fehler und stellen Sie sicher, dass die Anmeldedaten korrekt sind.
- **Logging-Probleme**: Stellen Sie sicher, dass das `logs`-Verzeichnis existiert und beschreibbar ist.


## 🤝 Mitwirken

Beiträge sind willkommen! Bitte fühlen Sie sich frei, Issues zu erstellen oder Pull Requests einzureichen.

1. Fork des Repositories
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/amazing-feature`)
3. Commit Ihrer Änderungen (`git commit -m 'Add some amazing feature'`)
4. Push zum Branch (`git push origin feature/amazing-feature`)
5. Öffnen Sie einen Pull Request 