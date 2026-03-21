#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Section Extractor
Extrahiert Abschnitt 15 und 16 aus einer PDF-Datei
"""

import re
import sys

def extract_sections_from_pdf(pdf_path):
    """Extrahiert Abschnitt 15 und 16 aus einer PDF-Datei"""
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 nicht installiert. Bitte installieren mit: pip install PyPDF2")
        return None
    
    try:
        pdf = open(pdf_path, 'rb')
        reader = PyPDF2.PdfReader(pdf)
        
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        pdf.close()
        
        # Extrahiere Abschnitt 15 und 16
        sections = {
            'section_15': extract_section(full_text, '15'),
            'section_16': extract_section(full_text, '16'),
            'section_3': extract_section(full_text, '3'),
            'ate_values': extract_ate_values(full_text)
        }
        
        return sections
        
    except Exception as e:
        print(f"Fehler beim Lesen der PDF: {e}")
        return None

def extract_ate_values(text):
    """Extrahiert ATE-Werte (Acute Toxicity Estimates) aus dem Text"""
    ate_values = {}
    
    # Muster für ATE-Werte
    ate_patterns = [
        r'ATE\s*\(?\s*oral\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/kg',
        r'ATE\s*\(?\s*dermal\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/kg',
        r'ATE\s*\(?\s*inhalation\s*,\s*vapour\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/L',
        r'ATE\s*\(?\s*inhalation\s*,\s*dust/mist\s*\)?\s*[:\s]*([\d.,>\<]+)\s*mg/L'
    ]
    
    # Suche nach "Acute Toxicity Estimate" Abschnitten
    # Das ist normalerweise in Abschnitt 3.2
    
    # Extrahiere alle ATE-Werte
    matches = re.findall(r'ATE\s*\([^)]+\)\s*[:\s]*([\d.,>\<]+)\s*(mg/kg|mg/L)', text)
    
    for match in matches:
        value = match[0].strip()
        unit = match[1].strip()
        
        # Bestimme den Typ basierend auf dem Kontext
        context_match = re.search(rf'ATE\s*\(([^)]+)\).*?{re.escape(value)}\s*{unit}', text[:500], re.IGNORECASE)
        if context_match:
            ate_type = context_match.group(1).lower()
            if 'oral' in ate_type:
                ate_values['oral'] = f"ATE (oral) {value} mg/kg"
            elif 'dermal' in ate_type:
                ate_values['dermal'] = f"ATE (dermal) {value} mg/kg"
            elif 'vapour' in ate_type or 'inhalation' in ate_type:
                ate_values['inhalation_vapour'] = f"ATE (inhalation, vapour) {value} mg/L"
            elif 'dust' in ate_type or 'mist' in ate_type:
                ate_values['inhalation_dust'] = f"ATE (inhalation, dust/mist) {value} mg/L"
    
    return ate_values

def extract_section(text, section_num):
    """Extrahiert einen bestimmten Abschnitt aus dem Text"""
    # Muster für Abschnitt 15 oder 16
    patterns = [
        f'(?i)SECTION\\s*{section_num}[:\\s].*?(?=SECTION\\s*\\d+\\s*:|$)',
        f'(?i){section_num}\\.\\s+.*?(?=\\d+\\.\\s+|$)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Nimm den längsten Treffer
            return max(matches, key=len).strip()
    
    return ""

def parse_section_15(text):
    """Parst Abschnitt 15 - Regulatory information"""
    result = {
        'eu_legislation': '',
        'national_legislation': []
    }
    
    # Suche nach EU legislation
    eu_match = re.search(r'(?i)EU.?legislation[:\s]*(.*?)(?=national|Regulation|$)', text, re.DOTALL)
    if eu_match:
        result['eu_legislation'] = eu_match.group(1).strip()
    
    # Suche nach national legislation
    national_matches = re.findall(r'(?i)(TRGS|Wasser Gefährdungs Klasse|Regulation)\s*[:\s]*([^\n]+)', text)
    for match in national_matches:
        result['national_legislation'].append({
            'label': match[0].strip(),
            'value': match[1].strip()
        })
    
    return result

def parse_section_16(text):
    """Parst Abschnitt 16 - Other information"""
    result = {
        'indication_of_changes': [],
        'abbreviations': [],
        'abbreviations_source_note': '',
        'literature_references': '',
        'training_advice': '',
        'additional_info_lines': []
    }
    
    # Indication of changes
    changes_match = re.search(r'(?i)Indication of changes[:\s]*(.*?)(?=abbreviation|key literature|$)', text, re.DOTALL)
    if changes_match:
        changes_text = changes_match.group(1)
        # Extrahiere einzelne Änderungen
        changes = re.findall(r'-\s*([^\n]+)', changes_text)
        result['indication_of_changes'] = [c.strip() for c in changes]
    
    # Abbreviations
    abbr_match = re.search(r'(?i)Key literature[:\s]*(.*?)(?=training|$)', text, re.DOTALL)
    if abbr_match:
        abbr_text = abbr_match.group(1)
        # Extrahiere Abkürzungen
        abbrs = re.findall(r'([A-Z]{2,})\s*[:\-]\s*([^\n,]+)', abbr_text)
        for abbr in abbrs:
            result['abbreviations'].append({
                'short': abbr[0].strip(),
                'long': abbr[1].strip()
            })
    
    # Training advice
    training_match = re.search(r'(?i)Training advice[:\s]*(.*?)(?=$)', text, re.DOTALL)
    if training_match:
        result['training_advice'] = training_match.group(1).strip()
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python pdf_section_extractor.py <pdf_datei>")
        return
    
    pdf_path = sys.argv[1]
    print(f"Lese PDF: {pdf_path}")
    
    sections = extract_sections_from_pdf(pdf_path)
    
    if sections:
        print("\n=== Abschnitt 15 ===")
        print(sections['section_15'][:500] if sections['section_15'] else "Nicht gefunden")
        
        print("\n=== Abschnitt 16 ===")
        print(sections['section_16'][:500] if sections['section_16'] else "Nicht gefunden")
        
        # Speichere als JSON
        import json
        
        parsed_15 = parse_section_15(sections['section_15'])
        parsed_16 = parse_section_16(sections['section_16'])
        
        output = {
            'section_15': parsed_15,
            'section_16': parsed_16
        }
        
        output_file = 'pdf_extracted_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\nDaten gespeichert in: {output_file}")
    else:
        print("Keine Daten gefunden")

if __name__ == '__main__':
    main()
