#!/usr/bin/env python3
"""
SDScom XML Parser v8
Extracts structured data from SDScom XML format using lxml for robust parsing.
"""
import logging
from lxml import etree
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_text(element: Optional[etree._Element], path: str, default: str = "") -> str:
    """Safely gets text content from an element using a namespace-agnostic XPath."""
    if element is None:
        return default
    try:
        # Create a namespace-agnostic path
        parts = path.split('/')
        new_parts = []
        for part in parts:
            if ':' in part:
                ns, tag = part.split(':', 1)
                new_parts.append(f"*[local-name()='{tag}']")
            else:
                new_parts.append(part)
        new_path = '/'.join(new_parts)
        
        nodes = element.xpath(new_path)
        if not nodes:
            return default
        return ' '.join(''.join(node.itertext()).strip() for node in nodes).strip()
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return default

def get_all_texts(element: Optional[etree._Element], path: str) -> List[str]:
    """Gets all text contents from a list of elements using a namespace-agnostic XPath."""
    if element is None:
        return []
    try:
        parts = path.split('/')
        new_parts = []
        for part in parts:
            if ':' in part:
                ns, tag = part.split(':', 1)
                new_parts.append(f"*[local-name()='{tag}']")
            else:
                new_parts.append(part)
        new_path = '/'.join(new_parts)
        return [node.text.strip() for node in element.xpath(new_path) if node.text]
    except Exception:
        return []

class NewSDScomParser:
    def __init__(self, xml_path: str):
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()
        self.data: Dict[str, Any] = {}

    def parse(self) -> Dict[str, Any]:
        logger.info(f"Parsing XML with new parser: {self.tree.docinfo.URL}")
        datasheet_list = self.root.xpath("//*[local-name()='Datasheet']")
        if not datasheet_list:
            raise ValueError("<Datasheet> tag not found")
        datasheet = datasheet_list[0]

        self.data['meta'] = self._parse_meta(datasheet)
        
        sections = {
            1: 'IdentificationSubstPrep', 2: 'HazardIdentification', 3: 'Composition',
            4: 'FirstAidMeasures', 5: 'FireFightingMeasures', 6: 'AccidentalReleaseMeasures',
            7: 'HandlingAndStorage', 8: 'ExposureControlPersonalProtection', 9: 'PhysicalChemicalProperties',
            10: 'StabilityReactivity', 11: 'ToxicologicalInformation', 12: 'EcologicalInformation',
            13: 'DisposalConsiderations', 14: 'TransportInformation', 15: 'RegulatoryInfo',
            16: 'OtherInformation'
        }

        for num, section_name in sections.items():
            section_elements = datasheet.xpath(f"./*[local-name()='{section_name}']")
            if section_elements:
                parse_func = getattr(self, f'_parse_section_{num}', None)
                if parse_func:
                    self.data[f'section_{num}'] = parse_func(section_elements[0])
        
        return self.data

    def _parse_meta(self, datasheet: etree._Element) -> Dict[str, str]:
        id_section = datasheet.xpath(".//*[local-name()='IdentificationSubstPrep']")[0]
        info_section = datasheet.xpath(".//*[local-name()='InformationFromExportingSystem']")[0]
        return {
            'product_name': get_text(id_section, './/ProductIdentity/TradeName'),
            'version': get_text(id_section, 'VersionNo'),
            'revision_date': get_text(id_section, 'RevisionDate'),
            'print_date': get_text(info_section, 'DateGeneratedExport'),
            'language': get_text(info_section, './/Language/FreetextLanguageCode'),
            'country': get_text(info_section, './/RegulationsRelatedToCountryOrRegion/RegulationsRelatedToCountryOrRegionCode'),
        }

    def _parse_section_1(self, section: etree._Element) -> Dict[str, Any]:
        supplier = section.xpath(".//*[local-name()='SupplierInformation']")[0] if section.xpath(".//*[local-name()='SupplierInformation']") else None
        emergency = section.xpath(".//*[local-name()='EmergencyPhone']")[0] if section.xpath(".//*[local-name()='EmergencyPhone']") else None
        
        # Extract Product Categories
        product_categories = section.xpath('.//RelevantIdentifiedUse/IdentifiedUse/ProductCategory')
        pc1_code = get_text(product_categories[0], 'PcCode') if len(product_categories) > 0 else ''
        pc1_text = get_text(product_categories[0], 'PcFulltext/FullText') if len(product_categories) > 0 else ''
        pc2_code = get_text(product_categories[1], 'PcCode') if len(product_categories) > 1 else ''
        pc2_text = get_text(product_categories[1], 'PcFulltext/FullText') if len(product_categories) > 1 else ''

        return {
            'product_identifier': {
                'trade_name': get_text(section, './/ProductIdentity/TradeName'),
                'item_no': get_text(section, 'ItemNo'),
                'ufi': get_text(section, './/ProductIdentity/Ufi'),
            },
            'relevant_uses': {
                'product_type': get_text(section, './/RelevantIdentifiedUse/ProductType/FullText'),
                'su': get_text(section, './/RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuCode'),
                'su_fulltext': get_text(section, './/RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuFulltext/FullText'),
                'pc1': f"{pc1_code}: {pc1_text}",
                'pc2': f"{pc2_code}: {pc2_text}",
            },
            'supplier_details': {
                'name': get_text(supplier, 'Name'),
                'address': f"{get_text(supplier, 'Address/PostAddressLine2')}, {get_text(supplier, 'Address/PostCode')} {get_text(supplier, 'Address/PostCity')}",
                'country': get_text(supplier, 'Country'),
                'phone': get_text(supplier, 'Phone'),
                'email': get_text(supplier, 'Email'),
                'website': get_text(supplier, 'CompanyUrl'),
            },
            'emergency_phone': {
                'number': get_text(emergency, 'No'),
                'description': get_text(emergency, 'EmergencyPhoneDescription/FullText'),
            }
        }

    def _parse_section_2(self, section: etree._Element) -> Dict[str, Any]:
        labelling_list = section.xpath('.//ClpLabellingInfo')
        labelling = labelling_list[0] if labelling_list else None
        return {
            'classification': [
                {
                    'category': get_text(c, 'ClpHazardClassCategory'),
                    'statement': get_text(c, 'ClpHazardStatement/FullText'),
                    'code': get_text(c, 'ClpHazardStatement/PhraseCode'),
                    'procedure': get_text(c, 'ClpClassificationProcedure/FullText'),
                }
                for c in section.xpath('.//ClpClassification/ClpHazardClassification')
            ],
            'labelling': {
                'pictograms': get_all_texts(labelling, 'ClpHazardPictogram/PhraseCode'),
                'signal_word': get_text(labelling, 'ClpSignalWord/FullText'),
                'hazard_statements': [
                    {'code': get_text(s, 'PhraseCode'), 'text': get_text(s, 'FullText')}
                    for s in labelling.xpath('ClpHazardStatement')
                ] if labelling is not None else [],
                'precautionary_statements': {
                    'prevention': [get_text(s, 'FullText') for s in labelling.xpath("ClpPrecautionaryStatement[contains(PhraseCode, '2')]")] if labelling is not None else [],
                    'response': [get_text(s, 'FullText') for s in labelling.xpath("ClpPrecautionaryStatement[starts-with(PhraseCode, '3')]")] if labelling is not None else [],
                }
            },
            'other_hazards': {
                'physicochemical': get_text(section, './/OtherHazardsInfo/PhysicochemicalEffect/FullText'),
                'health': get_text(section, './/OtherHazardsInfo/HealthEffect/FullText'),
            }
        }
        
    def _parse_section_3(self, section: etree._Element) -> Dict[str, Any]:
        components = []
        for c in section.xpath('Component'):
            # Basic component data
            component_data = {
                'name': get_text(c, './/GenericName'),
                'cas': get_text(c, './/CasNo'),
                'ec': get_text(c, './/EcNo'),
                'concentration': f"{get_text(c, './/Concentration/LowerValue')} - {get_text(c, './/Concentration/UpperValue')} {get_text(c, './/Concentration/Unit')}",
                'classification': [
                    f"{get_text(cl, 'ClpHazardClassCategory')}: {get_text(cl, 'ClpHazardStatement/FullText')}"
                    for cl in c.xpath('.//Classification/ClpHazardClassification')
                ],
                'toxicological_info': [],
                'ecological_info': [],
            }

            # Toxicological Information
            tox_info = c.find('.//ToxicologicalInformation')
            if tox_info is not None:
                for test_result in tox_info.xpath('.//TestResults'):
                    effect = get_text(test_result, 'EffectTested')
                    route = get_text(test_result, 'ExposureRoute')
                    value = get_text(test_result, 'Value')
                    species = get_text(test_result, 'Species/Value')
                    component_data['toxicological_info'].append(
                        f"{effect} {route}: {value} ({species})"
                    )

            # Ecological Information
            eco_info = c.find('.//EcologicalInformation')
            if eco_info is not None:
                for eco_test in eco_info.xpath('.//AquaticToxicity/*'):
                    value = get_text(eco_test, 'Value')
                    effect = get_text(eco_test, 'EffectDoseConcentration')
                    species = get_text(eco_test, 'Species')
                    method = get_text(eco_test, 'Method')
                    if value and effect and species:
                        info_str = f"{effect}: {value} ({species})"
                        if method:
                            info_str += f" - {method}"
                        component_data['ecological_info'].append(info_str)
            
            components.append(component_data)

        return {'mixture_components': components}
        
    def _parse_section_4(self, section: etree._Element) -> Dict[str, Any]:
        desc_list = section.xpath('DescriptionOfFirstAidMeasures')
        desc = desc_list[0] if desc_list else None
        return {
            'description': {
                'general': ' '.join(get_all_texts(desc, 'GeneralInformation/FullText')),
                'inhalation': ' '.join(get_all_texts(desc, 'FirstAidInhalation/FullText')),
                'skin': ' '.join(get_all_texts(desc, 'FirstAidSkin/FullText')),
                'eye': ' '.join(get_all_texts(desc, 'FirstAidEye/FullText')),
                'ingestion': ' '.join(get_all_texts(desc, 'FirstAidIngestion/FullText')),
                'self_protection': get_text(desc, 'PersonalProtectionFirstAider/FullText'),
            },
            'symptoms': get_text(section, './/InformationToHealthProfessionals/SymptomsAndEffectsGeneral/FullText'),
            'treatment': get_text(section, './/MedicalAttentionAndSpecialTreatmentNeeded/MedicalTreatment/FullText'),
        }

    # Stubs for remaining sections
    def _parse_section_5(self, section: etree._Element) -> Dict:
        return {
            'suitable_media': get_text(section, './/MediaToBeUsed'),
            'unsuitable_media': get_text(section, './/MediaNotBeUsed'),
            'special_hazards': get_text(section, './/FireAndExplosionHazards'),
            'combustion_products': get_text(section, './/HazardCombustionProd'),
            'firefighter_advice': get_text(section, './/SpecialProtectiveEquipmentForFirefighters'),
            'additional_info': get_text(section, './/FireAndExplosionComments'),
        }
    def _parse_section_6(self, section: etree._Element) -> Dict:
        return {
            'personal_precautions': get_text(section, './/ForNonEmergencyPersonnel/PersonalPrecautions'),
            'protective_equipment': get_text(section, './/ForNonEmergencyPersonnel/ProtectiveEquipment'),
            'emergency_responders': get_text(section, './/ForEmergencyResponders'),
            'environmental_precautions': get_text(section, './/EnvironmentalPrecautions'),
            'containment': get_text(section, './/ContainmentAndCleaningUp/Containment'),
            'cleaning': get_text(section, './/ContainmentAndCleaningUp/CleaningUp'),
            'other_sections': get_text(section, './/ReferenceToOtherSections'),
            'additional_info': get_text(section, './/AdditionalInformation'),
        }
    def _parse_section_7(self, section: etree._Element) -> Dict:
        return {
            'safe_handling': get_text(section, './/SafeHandling/HandlingPrecautions'),
            'fire_prevention': get_text(section, './/SafeHandling/MeasuresToPreventFire'),
            'occupational_hygiene': get_text(section, './/SafeHandling/GeneralOccupationalHygiene'),
            'storage_conditions': get_text(section, './/ConditionsForSafeStorage/TechnicalMeasuresAndStorageConditions'),
            'storage_rooms': get_text(section, './/ConditionsForSafeStorage/RequirementsForStorageRoomsAndVessels'),
            'storage_assembly': get_text(section, './/ConditionsForSafeStorage/HintsOnStorageAssembly'),
            'storage_class': get_text(section, './/ConditionsForSafeStorage/StorageClass'),
            'specific_end_use': get_text(section, './/SpecificEndUses'),
        }
    def _parse_section_8(self, section: etree._Element) -> Dict:
        return {
            'control_parameters': get_text(section, './/ControlParameters'),
            'respiratory_protection': get_text(section, './/PersonalProtectionEquipment/RespiratoryProtection'),
            'eye_protection': get_text(section, './/PersonalProtectionEquipment/EyeProtection'),
            'skin_protection': get_text(section, './/PersonalProtectionEquipment/SkinProtection'),
            'environmental_exposure': get_text(section, './/EnvironmentalExposureControls'),
        }
    def _parse_section_9(self, section: etree._Element) -> Dict:
        
        def get_value_temp_method(elem_name):
            base_path = f".//SafetyRelevantInformation/{elem_name}"
            base_element = section.find(base_path)
            if base_element is None:
                return "No data available", "", ""

            value = ' '.join(base_element.xpath(".//Value//text() | .//UnitValue//text() | .//OtherMediumDescription//text()")).strip()
            temp = ' '.join(base_element.xpath(".//Temperature//text()")).strip()
            method = ' '.join(base_element.xpath(".//Method//text()")).strip()
            
            # Special handling for some tags
            if not value:
                 value = get_text(base_element, '.')

            # Fallback for completely empty elements
            if not value and not temp and not method:
                return "No data available", "", ""

            return value, temp, method

        parameters = [
            ("pH", "PhValue"),
            ("Melting point", "MeltingPointRelated"),
            ("Freezing point", "FreezingPoint"),
            ("Initial boiling point and boiling range", "BoilingPointRelated"),
            ("Flash point", "FlashPoint"),
            ("Evaporation rate", "EvaporationRate"),
            ("Auto-ignition temperature", "AutoIgnitionTemperature"),
            ("Upper/lower flammability or explosive limits", "ExplosionLimit"),
            ("Vapour pressure", "VapourPressure"),
            ("Vapour density", "VapourDensity"),
            ("Density", "Densities"),
            ("Bulk density", "BulkDensity"),
            ("Water solubility", "Solubilities"),
            ("Dynamic viscosity", "DynamicViscosity"),
            ("Kinematic viscosity", "KinematicViscosity"),
        ]

        safety_data = []
        for name, tag in parameters:
            val, temp, meth = get_value_temp_method(tag)
            safety_data.append({
                'parameter': name,
                'value': val,
                'temperature': temp,
                'method': meth,
            })
        
        return {
            'appearance': get_text(section, './/Appearance'),
            'safety_data': safety_data
        }
    def _parse_section_10(self, section: etree._Element) -> Dict:
        return {
            'reactivity': get_text(section, './/ReactivityDescription'),
            'chemical_stability': get_text(section, './/StabilityDescription'),
            'hazardous_reactions': get_text(section, './/HazardousReactions'),
            'conditions_to_avoid': get_text(section, './/ConditionsToAvoid'),
            'incompatible_materials': get_text(section, './/MaterialsToAvoid'),
            'hazardous_decomposition': get_text(section, './/HazardousDecompositionProducts'),
        }
    def _parse_section_11(self, section: etree._Element) -> Dict:
        return {
            'acute_toxicity': get_text(section, './/AcuteToxicity'),
            'skin_corrosion': get_text(section, './/SkinCorrosionIrritation'),
            'eye_damage': get_text(section, './/EyeDamageOrIrritation'),
            'sensitisation': get_text(section, './/RespiratoryOrSkinSensitisation'),
            'mutagenicity': get_text(section, './/GermCellMutagenicity'),
            'carcinogenicity': get_text(section, './/Carcinogenicity'),
            'reproductive_toxicity': get_text(section, './/ReproductiveToxicity'),
            'stot_single': get_text(section, './/SpecificTargetOrganSE'),
            'stot_repeated': get_text(section, './/SpecificTargetOrganRE'),
            'aspiration_hazard': get_text(section, './/AspirationHazard'),
        }
    def _parse_section_12(self, section: etree._Element) -> Dict:
        return {
            'aquatic_toxicity': get_text(section, './/AquaticToxicity'),
            'sediment_toxicity': get_text(section, './/SedimentToxicity'),
            'terrestrial_toxicity': get_text(section, './/TerrestrialToxicity'),
            'persistence': get_text(section, './/PersistenceDegradability'),
            'bioaccumulation': get_text(section, './/Bioaccumulation'),
            'mobility': get_text(section, './/Mobility'),
            'additional_ecotox': get_text(section, './/AdditionalEcotoxInformation'),
        }
    def _parse_section_13(self, section: etree._Element) -> Dict:
        return {
            'waste_treatment': get_text(section, './/WasteTreatment'),
            'eu_requirements': get_text(section, './/EuRequirements'),
        }
    def _parse_section_14(self, section: etree._Element) -> Dict:
        # Helper to get text from a specific transport sub-element
        def get_transport_text(base_element, transport_type, path, default=""):
            return get_text(base_element, f".//{transport_type}/{path}", default)

        # Helper for substance names which can be multiple
        def get_substances(base_element, transport_type, path):
            return ', '.join(get_all_texts(base_element, f".//{transport_type}/{path}"))

        return {
            'land': {
                'un_number': get_text(section, './/UnNoAdrRid'),
                'shipping_name': f"{get_text(section, './/AdrRid/ProperShippingNameNationalAdrRid/FullText')} ({get_substances(section, 'AdrRid', 'DangerReleasingSubstanceEnglishAdrRid/FullText')})",
                'transport_class': get_text(section, './/AdrRid/ClassAdrRid'),
                'packing_group': get_text(section, './/PackingGroupAdrRid'),
                'environmental_hazards': get_text(section, './/EnvironmHazardAccordAdrRid/FullText'),
                'special_provisions': get_text(section, './/AdrRidOtherInformation/AdrRidSpecialProvisions'),
                'limited_quantity': get_text(section, './/AdrRidOtherInformation/AdrRidLimitedQty'),
                'excepted_quantities': get_text(section, './/AdrRidOtherInformation/AdrRidExceptedQty'),
                'hazard_id': get_text(section, './/AdrRidOtherInformation/AdrHazardIdentificationNo'),
                'classification_code': get_text(section, './/AdrRid/ClassCodeAdrRid'),
                'tunnel_code': get_text(section, './/AdrRidOtherInformation/AdrTunnelRestrictionCode'),
            },
            'inland': {
                'un_number': get_text(section, './/UnNoAdn'),
                'shipping_name': f"{get_text(section, './/Adn/ProperShippingNameNationalAdn/FullText')} ({get_substances(section, 'Adn', 'DangerReleasingSubstanceEnglishAdn/FullText')})",
                'transport_class': get_text(section, './/Adn/ClassAdn'),
                'packing_group': get_text(section, './/PackingGroupAdn'),
                'environmental_hazards': get_text(section, './/EnvironmHazardAccordAdn/FullText'),
                'special_provisions': get_text(section, './/AdnOtherInformation/AdnSpecialProvisions'),
                'limited_quantity': get_text(section, './/AdnOtherInformation/AdnLimitedQty'),
                'excepted_quantities': get_text(section, './/AdnOtherInformation/AdnExceptedQty'),
                'classification_code': get_text(section, './/Adn/ClassCodeAdn'),
            },
            'sea': {
                'un_number': get_text(section, './/UnNoImdg'),
                'shipping_name': f"{get_text(section, './/Imdg/ProperShippingNameEnglishImdg/FullText')} ({get_substances(section, 'Imdg', 'DangerReleasingSubstanceEnglishImdg/FullText')})",
                'transport_class': get_text(section, './/Imdg/ClassImdg'),
                'packing_group': get_text(section, './/PackingGroupImdg'),
                'environmental_hazards': get_text(section, './/Imdg/EnvironmHazardAccordImdg/FullText'),
                'special_provisions': get_text(section, './/ImdgOtherInformation/ImdgSpecialProvisions'),
                'limited_quantity': get_text(section, './/ImdgOtherInformation/ImdgLimitedQty'),
                'excepted_quantities': get_text(section, './/ImdgOtherInformation/ImdgExceptedQty'),
                'ems_code': get_text(section, './/ImdgOtherInformation/ImdgEmsCode'),
            },
            'air': {
                'un_number': get_text(section, './/UnNoIcao'),
                'shipping_name': f"{get_text(section, './/Icao/ProperShippingNameEnglishIcao/FullText')} ({get_substances(section, 'Icao', 'DangerReleasingSubstanceEnglishIcao/FullText')})",
                'transport_class': get_text(section, './/IcaoIata/ClassIcaoIata'),
                'packing_group': get_text(section, './/PackingGroupIcaoIata'),
                'environmental_hazards': get_text(section, './/EnvironmHazardAccordIcaoIata/FullText'),
                'special_provisions': get_text(section, './/IcaoIataOtherInformation/IcaoIataSpecialProvisions'),
                'limited_quantity': get_text(section, './/IcaoIataOtherInformation/IcaoIataLimitedQty'),
                'excepted_quantities': get_text(section, './/IcaoIataOtherInformation/IcaoIataExemptedQty'),
            },
            'bulk_transport': get_text(section, './/TransportInBulk'),
        }
    def _parse_section_15(self, section: etree._Element) -> Dict:
        national_legislation = []
        national_legislation_node = section.find('.//NationalLegislationGermany')
        if national_legislation_node is not None:
            for elem in national_legislation_node:
                text = ' '.join(elem.itertext()).strip()
                if text:
                    tag_name = elem.tag.replace('_', ' ').title()
                    national_legislation.append({'label': tag_name, 'value': text})

        return {
            'eu_legislation': get_text(section, './/SpecificProvisionsRelatedToProduct/EuLegislation'),
            'national_legislation': national_legislation,
        }
    def _parse_section_16(self, section: etree._Element) -> Dict:
        return {
            'other_info': get_text(section, '.'),
        }


def parse_sds_xml(xml_path: str) -> Dict[str, Any]:
    """Factory function to instantiate and run the parser."""
    try:
        parser = NewSDScomParser(xml_path)
        return parser.parse()
    except Exception as e:
        logger.error(f"Fatal error during XML parsing: {e}", exc_info=True)
        return {}

if __name__ == '__main__':
    # Example usage for testing
    import os
    xml_file = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
    if os.path.exists(xml_file):
        parsed_data = parse_sds_xml(xml_file)
        if parsed_data:
            import json
            # Output to a file for inspection
            with open('parsed_sds_data.json', 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            print("Parsing successful. Data saved to parsed_sds_data.json")
        else:
            print("Parsing failed.")
    else:
        print(f"Test file not found: {xml_file}")
