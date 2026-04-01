#!/usr/bin/env python3
"""
SDS XML Importer v7
Renders an HTML template with data parsed from an SDScom XML file.
"""
import logging
import os
from jinja2 import Environment, FileSystemLoader
from sds_parser import parse_sds_xml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_sds_to_html(xml_path: str, template_path: str) -> str:
    """
    Parses an SDScom XML file and injects its data into a Jinja2 HTML template.

    Args:
        xml_path: The file path of the SDScom XML file.
        template_path: The file path of the Jinja2 HTML template.

    Returns:
        The rendered HTML as a string, or an empty string if an error occurs.
    """
    logger.info(f"Starting import process for {xml_path}")

    # 1. Parse the XML file
    try:
        logger.info(f"Parsing XML file: {xml_path}")
        sds_data = parse_sds_xml(xml_path)
        if not sds_data:
            logger.error("XML parsing resulted in empty data.")
            return ""
        logger.info(f"XML parsed successfully. Keys: {list(sds_data.keys())}")
    except Exception as e:
        logger.error(f"Failed to parse XML file {xml_path}: {e}", exc_info=True)
        return ""

    # 2. Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    # 3. Render the template
    try:
        template = env.get_template(template_file)
        rendered_html = template.render(sds_data)
        logger.info("Successfully rendered HTML template.")
        return rendered_html
    except Exception as e:
        logger.error(f"Failed to render HTML template {template_path}: {e}", exc_info=True)
        return ""

if __name__ == '__main__':
    # Configuration for standalone execution
    XML_FILE = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
    TEMPLATE_FILE = 'layout-placeholders-fixed-v2.html'
    OUTPUT_FILE = 'importer_output.html'

    # Ensure input files exist
    if not os.path.exists(XML_FILE):
        print(f"Error: XML file not found at '{XML_FILE}'")
    elif not os.path.exists(TEMPLATE_FILE):
        print(f"Error: Template file not found at '{TEMPLATE_FILE}'")
    else:
        # Run the import process
        final_html = import_sds_to_html(XML_FILE, TEMPLATE_FILE)

        # Write the output
        if final_html:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"Import successful. Output written to '{OUTPUT_FILE}'")
        else:
            print("Import failed. Check logs for details.")
