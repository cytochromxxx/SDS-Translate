# Tasks: SDS Hybrid Parser & Validator System

## Phase 1: Erweitern des bestehenden Parsers

### 1. Bestehenden Code analysieren und vorbereiten
- [x] 1.1 Hardcodierte Daten in `sds_parser.py` identifizieren
  - [x] 1.1.1 Section 8 OEL-Tabelle (Zeile 238-242) entfernen
  - [x] 1.1.2 Andere hardcodierte Werte finden und markieren
- [x] 1.2 Dependencies hinzufügen
  - [x] 1.2.1 `pdfplumber` zu requirements.txt hinzufügen
  - [x] 1.2.2 Dependencies installieren


### 2. PDF-Extraktor für kritische Lücken erstellen
- [x] 2.1 Neue Datei `pdf_gap_filler.py` erstellen
- [x] 2.2 Section 8 OEL-Tabelle aus PDF extrahieren
- [x] 2.3 Section 16 Daten aus PDF extrahieren
- [x] 2.4 In `sds_parser.py` integrieren: Falls XML leer → PDF nutzen

### 3. Bestehenden Parser erweitern
- [x] 3.1 `_parse_section_8()` in `sds_parser.py` anpassen
  - [x] 3.1.1 Hardcoded OEL-Daten entfernen
  - [x] 3.1.2 PDF-Fallback hinzufügen wenn XML leer
- [x] 3.2 `_parse_section_16()` erweitern
  - [x] 3.2.1 PDF-Fallback für leeres `<OtherInformation/>`
- [x] 3.3 Weitere Lücken füllen (Section 1, 12, 15)
  - [x] 3.3.1 Section 1: Life Cycle Stage aus PDF extrahieren
  - [x] 3.3.2 Section 12: Mobility, Endocrine, Adverse Effects aus PDF
  - [x] 3.3.3 Section 15: EU Legislation aus PDF

## Phase 2: Validierung & Reporting

### 4. Einfacher Validator
- [x] 4.1 Neue Datei `sds_validator.py` erstellen
- [x] 4.2 Funktion `check_completeness()` - prüft ob Pflichtfelder vorhanden
- [x] 4.3 Funktion `generate_gap_report()` - Markdown-Report erstellen

### 5. Integration & Testing
- [x] 5.1 `sds_xml_importer.py` erweitern
  - [x] 5.1.1 Validierung vor Template-Rendering
  - [x] 5.1.2 Gap-Report bei Lücken anzeigen
- [x] 5.2 End-to-End Test mit Mycoplasma Off SDS
  - [x] 5.2.1 XML parsen mit PDF-Fallback
  - [x] 5.2.2 Validierung durchführen
  - [x] 5.2.3 HTML-Output prüfen

## Geschätzte Zeit: 3-5 Tage

---

## Hinweise zur Implementierung

**Priorität der Datenquellen:**
1. XML-Daten (primär)
2. PDF-Daten (nur für identifizierte Lücken)

**Kritische Lücken:**
- Section 8: OEL-Tabelle (aktuell hardcoded in Zeile 238-242)
- Section 16: Komplett leer (Abkürzungen, Literatur, Klassifizierungen)
- Section 15: EU Legislation leer
- Section 12: Mobility, Endocrine, Adverse Effects leer
- Section 1: Life Cycle Stage fehlt
