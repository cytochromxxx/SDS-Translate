#!/usr/bin/env python3
"""
End-to-End Test: Mycoplasma Off SDS
Tasks 5.2, 5.2.1, 5.2.2, 5.2.3
"""
import os
import sys

XML_FILE = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
PDF_FILE = 'SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf'
TEMPLATE_FILE = 'layout-placeholders-fixed-v2.html'
GAP_REPORT_FILE = 'gap_report.md'
HTML_OUTPUT_FILE = 'e2e_test_output.html'

print("=" * 70)
print("END-TO-END TEST: Mycoplasma Off SDS")
print("=" * 70)

# ── Task 5.2.1: Parse XML with PDF fallback ──────────────────────────────────
print("\n[5.2.1] Parsing XML with PDF fallback...")
from sds_parser import parse_sds_xml

data = parse_sds_xml(
    XML_FILE,
    pdf_path=PDF_FILE
)

print(f"  Parsed keys: {list(data.keys())}")

# Verify Section 8 OEL
oel = data.get('section_8', {}).get('occupational_exposure_limits', [])
print(f"\n  Section 8 - OEL entries: {len(oel)}")
if oel:
    print(f"    First entry: {oel[0]}")
    print("  ✅ Section 8 OEL filled from PDF")
else:
    print("  ❌ Section 8 OEL still empty")

# Verify Section 16 abbreviations
abbrevs = data.get('other_information', {}).get('abbreviations', [])
print(f"\n  Section 16 - Abbreviations: {len(abbrevs)}")
if abbrevs:
    print(f"    First entry: {abbrevs[0]}")
    print("  ✅ Section 16 abbreviations filled from PDF")
else:
    print("  ❌ Section 16 abbreviations still empty")

# Verify Section 1 LCS
lcs = data.get('section_1', {}).get('relevant_uses', {}).get('lcs', '')
print(f"\n  Section 1 - LCS: '{lcs}'")
if lcs:
    print("  ✅ Section 1 LCS filled from PDF")
else:
    print("  ⚠️  Section 1 LCS still empty")

# Verify Section 15 EU legislation
eu_leg = data.get('section_15', {}).get('eu_legislation', '')
print(f"\n  Section 15 - EU legislation (first 100 chars): '{str(eu_leg)[:100]}'")
if eu_leg:
    print("  ✅ Section 15 EU legislation filled from PDF")
else:
    print("  ⚠️  Section 15 EU legislation still empty")

# ── Task 5.2.2: Run validation ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("[5.2.2] Running validation...")
from sds_validator import validate_and_report

validation_result, gap_report = validate_and_report(data)

overall_status = validation_result['overall_status']
overall_completeness = validation_result['overall_completeness']
completeness_pct = round(overall_completeness * 100, 1)

print(f"\n  Overall status:       {overall_status.upper()}")
print(f"  Overall completeness: {completeness_pct}%")
print(f"  Total fields:         {validation_result['total_fields']}")
print(f"  Present fields:       {validation_result['present_fields']}")
print(f"  Missing fields:       {validation_result['missing_fields']}")
print(f"  Critical gaps:        {len(validation_result['critical_gaps'])}")
print(f"  Warnings:             {len(validation_result['warnings'])}")

if overall_status in ('pass', 'warning'):
    print(f"\n  ✅ Validation status is '{overall_status}' (not 'fail')")
else:
    print(f"\n  ❌ Validation status is 'fail'")

if overall_completeness > 0.8:
    print(f"  ✅ Completeness {completeness_pct}% > 80%")
else:
    print(f"  ❌ Completeness {completeness_pct}% <= 80%")

if validation_result['critical_gaps']:
    print("\n  Critical gaps remaining:")
    for gap in validation_result['critical_gaps']:
        print(f"    ❌ {gap}")

if validation_result['warnings']:
    print("\n  Warnings:")
    for w in validation_result['warnings']:
        print(f"    ⚠️  {w}")

# ── Task 5.2.3: Check HTML output ────────────────────────────────────────────
print("\n" + "=" * 70)
print("[5.2.3] Generating HTML output...")
from sds_xml_importer import import_sds_to_html

html, html_gap_report = import_sds_to_html(
    XML_FILE,
    TEMPLATE_FILE,
    pdf_path=PDF_FILE
)

print(f"\n  HTML length: {len(html)} characters")

if html:
    print("  ✅ HTML is not empty")
    # Check for expected content
    checks = [
        ("Mycoplasma", "product name"),
        ("SECTION", "section headers"),
        ("propan", "chemical content"),
    ]
    for keyword, label in checks:
        if keyword.lower() in html.lower():
            print(f"  ✅ HTML contains {label} ('{keyword}')")
        else:
            print(f"  ⚠️  HTML does not contain {label} ('{keyword}')")
else:
    print("  ❌ HTML is empty!")

# ── Save results ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Saving results...")

# Save gap report
report_to_save = gap_report or html_gap_report
if report_to_save:
    with open(GAP_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_to_save)
    print(f"  ✅ Gap report saved to '{GAP_REPORT_FILE}'")
else:
    # Generate and save even if no gaps (for documentation)
    with open(GAP_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(gap_report)
    print(f"  ✅ Gap report saved to '{GAP_REPORT_FILE}' (no critical gaps)")

# Save HTML output
if html:
    with open(HTML_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✅ HTML output saved to '{HTML_OUTPUT_FILE}'")
else:
    print(f"  ❌ HTML output not saved (empty)")

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  XML + PDF parsing:    {'✅ OK' if data else '❌ FAILED'}")
print(f"  Section 8 OEL:        {'✅ ' + str(len(oel)) + ' entries' if oel else '❌ empty'}")
print(f"  Section 16 abbrevs:   {'✅ ' + str(len(abbrevs)) + ' entries' if abbrevs else '❌ empty'}")
print(f"  Section 1 LCS:        {'✅ filled' if lcs else '⚠️  empty'}")
print(f"  Section 15 EU leg:    {'✅ filled' if eu_leg else '⚠️  empty'}")
print(f"  Validation status:    {overall_status.upper()} ({completeness_pct}%)")
print(f"  HTML output:          {'✅ ' + str(len(html)) + ' chars' if html else '❌ empty'}")
print(f"  Gap report:           {GAP_REPORT_FILE}")
print(f"  HTML file:            {HTML_OUTPUT_FILE}")
print("=" * 70)
sys.exit(0)
