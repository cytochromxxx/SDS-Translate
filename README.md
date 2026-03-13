# SDS-Translate

SDS-Translate ist eine Flask-basierte Webanwendung zur Übersetzung von Sicherheitsdatenblättern (Safety Data Sheets, SDS).

## Funktionen

- **HTML-Upload**: Laden Sie eigene HTML-Sicherheitsdatenblätter hoch
- **PDF-Import**: Importieren Sie PDF-Dateien und konvertieren Sie diese in HTML
- **XML-Import**: SDScom-XML-Dateien importieren
- **Mehrsprachige Übersetzung**: Übersetzen Sie Dokumente in über 20 Sprachen
- **Phrasen-Bibliothek**: Verwenden Sie eine Datenbank mit vordefinierten Übersetzungen
- **Quick-Edit**: Korrigieren Sie mehrere Phrasen gleichzeitig
- **PDF-Export**: Exportieren Sie übersetzte Dokumente als PDF

## Installation

1. Installieren Sie die Abhängigkeiten:
```bash
pip install -r requirements.txt
```

2. Starten Sie die Anwendung:
```bash
python app.py
```

3. Öffnen Sie Ihren Browser und gehen Sie zu:
```
http://localhost:5000
```

## Verwendete Technologien

- **Backend**: Python, Flask
- **Datenbank**: SQLite
- **PDF-Generierung**: WeasyPrint
- **Frontend**: HTML, CSS, JavaScript

## Ordnerstruktur

```
.
├── app.py                    # Hauptanwendung
├── sds_translator_v4.py      # Übersetzungsmodul
├── sds_parser.py             # PDF-Parser
├── sdscom_parser.py          # SDScom-XML-Parser
├── phrases_library.db         # Phrasen-Datenbank
├── templates/                 # HTML-Templates
├── ghs/                      # GHS-Piktogramme
└── requirements.txt          # Python-Abhängigkeiten
```

## Lizenz

MIT License
