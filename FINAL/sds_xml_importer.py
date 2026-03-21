#!/usr/bin/env python3
"""
SDS XML Importer v8
Renders an HTML template with data parsed from an SDScom XML file.
Includes validation and gap reporting via sds_validator.py.
"""
import logging
import os
from typing import Optional, Tuple
from jinja2 import Environment, FileSystemLoader
from sds_parser import parse_sds_xml
from sds_validator import validate_and_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_sds_to_html(
    xml_path: str,
    template_path: str,
    pdf_path: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Parses an SDScom XML file and injects its data into a Jinja2 HTML template.
    Optionally accepts a companion PDF path for hybrid gap-filling.
    After parsing, validates completeness and generates a gap report.

    Args:
        xml_path:      The file path of the SDScom XML file.
        template_path: The file path of the Jinja2 HTML template.
        pdf_path:      Optional path to the companion PDF file.
                       When provided, empty XML fields are filled from the PDF.

    Returns:
        A tuple (rendered_html, gap_report_markdown).
        - rendered_html is the rendered HTML string, or "" on error.
        - gap_report_markdown is a Markdown string when gaps exist, else None.

    Note:
        Backward compatible: callers that only pass xml_path and template_path
        continue to work exactly as before (gap_report is simply ignored).
    """
    logger.info(f"Starting import process for {xml_path}")

    # 1. Parse the XML file (with optional PDF gap-filling)
    try:
        if pdf_path:
            logger.info(f"Parsing XML file with PDF fallback: {xml_path} + {pdf_path}")
        else:
            logger.info(f"Parsing XML file: {xml_path}")

        sds_data = parse_sds_xml(xml_path, pdf_path=pdf_path)
        if not sds_data:
            logger.error("XML parsing resulted in empty data.")
            return "", None
        logger.info(f"XML parsed successfully. Keys: {list(sds_data.keys())}")
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}", exc_info=True)
        return "", None

    # 2. Validate completeness and generate gap report
    gap_report_md: Optional[str] = None
    try:
        validation_result, gap_report_md = validate_and_report(sds_data)
        overall_status = validation_result.get("overall_status", "unknown")
        completeness_pct = round(validation_result.get("overall_completeness", 0) * 100, 1)

        if overall_status == "fail":
            logger.warning(
                f"Validation FAILED for {xml_path}: "
                f"completeness={completeness_pct}%, "
                f"critical_gaps={len(validation_result.get('critical_gaps', []))}. "
                "Proceeding with template rendering (backward-compatible mode)."
            )
        elif overall_status == "warning":
            logger.warning(
                f"Validation WARNING for {xml_path}: "
                f"completeness={completeness_pct}%, "
                f"warnings={len(validation_result.get('warnings', []))}."
            )
        else:
            logger.info(f"Validation PASSED for {xml_path}: completeness={completeness_pct}%.")
            # No gaps – no need to carry the report forward
            gap_report_md = None

    except Exception as e:
        logger.error(f"Validation step failed for {xml_path}: {e}", exc_info=True)
        gap_report_md = None

    # 3. Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    # Register custom filters
    def pad_filter(value, width, fillchar='0', left=True):
        """Zero-pad (or any char) a value to a given width."""
        s = str(value)
        if left:
            return s.zfill(int(width)) if fillchar == '0' else s.rjust(int(width), fillchar)
        return s.ljust(int(width), fillchar)

    env.filters['pad'] = pad_filter

    # 4. Render the template
    try:
        template = env.get_template(template_file)
        rendered_html = template.render(sds_data)
        logger.info("Successfully rendered HTML template.")
        return rendered_html, gap_report_md
    except Exception as e:
        logger.error(f"Failed to render HTML template {template_path}: {e}", exc_info=True)
        return "", gap_report_md


if __name__ == '__main__':
    # Configuration for standalone execution
    XML_FILE = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
    TEMPLATE_FILE = 'layout-placeholders-fixed-v2.html'
    OUTPUT_FILE = 'importer_output.html'
    GAP_REPORT_FILE = 'gap_report.md'
    PDF_FILE = 'SDS_Mycoplasma_Off_15-5xxx_en_DE_Ver.05.pdf'

    # Resolve optional PDF path
    pdf = PDF_FILE if os.path.exists(PDF_FILE) else None
    if pdf:
        print(f"PDF companion found: {pdf}")
    else:
        print("No companion PDF found – running XML-only mode.")

    # Ensure input files exist
    if not os.path.exists(XML_FILE):
        print(f"Error: XML file not found at '{XML_FILE}'")
    elif not os.path.exists(TEMPLATE_FILE):
        print(f"Error: Template file not found at '{TEMPLATE_FILE}'")
    else:
        # Run the import process
        final_html, gap_report = import_sds_to_html(XML_FILE, TEMPLATE_FILE, pdf_path=pdf)

        # Write the HTML output
        if final_html:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"Import successful. Output written to '{OUTPUT_FILE}'")
        else:
            print("Import failed. Check logs for details.")

        # Write the gap report if gaps were found
        if gap_report:
            with open(GAP_REPORT_FILE, 'w', encoding='utf-8') as f:
                f.write(gap_report)
            print(f"Gap report written to '{GAP_REPORT_FILE}'")
        else:
            print("No gaps detected – gap report not generated.")
