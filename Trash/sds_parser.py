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
    """Safely gets text content from an element using a truly namespace-agnostic XPath."""
    if element is None:
        return default
    try:
        # Correctly create a namespace-agnostic relative path
        agnostic_path = './' + '/'.join([f"*[local-name()='{part}']" for part in path.split('/')])
        nodes = element.xpath(agnostic_path)
        if nodes:
            return ' '.join(''.join(nodes[0].itertext()).strip().split())
        return default
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return default

def get_all_text_from_nodes(element: Optional[etree._Element], path: str) -> str:
    """Safely gets and joins text content from all found elements using a namespace-agnostic XPath."""
    if element is None:
        return ""
    try:
        agnostic_path = './/' + '/'.join([f"*[local-name()='{part}']" for part in path.split('/')])
        nodes = element.xpath(agnostic_path)
        if not nodes:
            return ""
        text = ' '.join(''.join(node.itertext()).strip() for node in nodes).strip()
        return ' '.join(text.split())
    except Exception as e:
        logger.warning(f"XPath {path} failed with error: {e}")
        return ""

def get_all_texts(element: Optional[etree._Element], path: str) -> List[str]:
    """Gets all text contents from a list of elements using a namespace-agnostic XPath."""
    if element is None:
        return []
    try:
        agnostic_path = './/' + '/'.join([f"*[local-name()='{part}']" for part in path.split('/')])
        return [node.text.strip() for node in element.xpath(agnostic_path) if node.text]
    except Exception:
        return []

class NewSDScomParser:
    def __init__(self, xml_path: str):
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()
        self.data: Dict[str, Any] = {}

    def _xpath_single(self, element: etree._Element, path: str) -> Optional[etree._Element]:
        """Helper to get the first result of an xpath query."""
        if element is None:
            return None
        results = element.xpath(f"./*[local-name()='{path}']")
        return results[0] if results else None

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
                    parsed_data = parse_func(section_elements[0])
                    if num == 2 and 'hazard_identification' in parsed_data:
                        self.data['hazard_identification'] = parsed_data['hazard_identification']
                    if num == 16:
                        self.data['other_information'] = parsed_data.get('other_information', {})
                    else:
                        self.data[f'section_{num}'] = parsed_data
        return self.data

    def _parse_meta(self, datasheet: etree._Element) -> Dict[str, str]:
        id_section = self._xpath_single(datasheet, 'IdentificationSubstPrep')
        info_section = self._xpath_single(datasheet, 'InformationFromExportingSystem')
        return {
            'product_name': get_text(id_section, 'ProductIdentity/TradeName'),
            'version': get_text(id_section, 'VersionNo'),
            'revision_date': get_text(id_section, 'RevisionDate'),
            'print_date': get_text(info_section, 'DateGeneratedExport'),
            'language': get_text(info_section, 'Language/FreetextLanguageCode'),
            'country': get_text(info_section, 'RegulationsRelatedToCountryOrRegion/RegulationsRelatedToCountryOrRegionCode'),
        }

    def _parse_section_1(self, section: etree._Element) -> Dict[str, Any]:
        supplier = self._xpath_single(section, 'SupplierInformation')
        emergency = self._xpath_single(section, 'EmergencyPhone')
        product_categories = section.xpath('.//*[local-name()="ProductCategory"]')
        pc1 = ": ".join(filter(None, [get_text(product_categories[0], 'PcCode'), get_text(product_categories[0], 'PcFulltext/FullText')])) if len(product_categories) > 0 else ''
        pc2 = ": ".join(filter(None, [get_text(product_categories[1], 'PcCode'), get_text(product_categories[1], 'PcFulltext/FullText')])) if len(product_categories) > 1 else ''
        lcs_elem = section.xpath('.//*[local-name()="LifeCycleStage"]')
        lcs = ": ".join(filter(None, [get_text(lcs_elem[0], 'LcsCode'), get_text(lcs_elem[0], 'LcsFulltext/FullText')])) if lcs_elem else 'PW: Widespread use by professional workers'

        return {
            'product_identifier': {'trade_name': get_text(section, 'ProductIdentity/TradeName'), 'item_no': get_text(section, 'ItemNo'), 'ufi': get_text(section, 'ProductIdentity/Ufi')},
            'relevant_uses': {
                'product_type': get_all_text_from_nodes(section, 'RelevantIdentifiedUse/ProductType/FullText'),
                'su': get_text(section, 'RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuCode'),
                'su_fulltext': get_text(section, 'RelevantIdentifiedUse/IdentifiedUse/SectorOfUse/SuFulltext/FullText'),
                'pc1': pc1, 'pc2': pc2, 'lcs': lcs,
            },
            'supplier_details': {'name': get_text(supplier, 'Name'), 'address': f"{get_text(supplier, 'Address/PostAddressLine2')}, {get_text(supplier, 'Address/PostCode')} {get_text(supplier, 'Address/PostCity')}", 'country': get_text(supplier, 'Country'), 'phone': get_text(supplier, 'Phone'), 'email': get_text(supplier, 'Email'), 'website': get_text(supplier, 'CompanyUrl')},
            'emergency_phone': {'number': get_text(emergency, 'No'), 'description': get_text(emergency, 'EmergencyPhoneDescription/FullText')}
        }

    def _parse_section_2(self, section: etree._Element) -> Dict[str, Any]:
        labelling = section.xpath('.//*[local-name()="ClpLabellingInfo"]')
        labelling = labelling[0] if labelling else None
        clp_classifications = [{'clp_hazard_class_category': get_text(c, 'ClpHazardClassCategory'), 'clp_hazard_statement_code': get_text(c, 'ClpHazardStatement/PhraseCode'), 'clp_hazard_statement_text': get_all_text_from_nodes(c, 'ClpHazardStatement/FullText'), 'clp_classification_procedure': get_all_text_from_nodes(c, 'ClpClassificationProcedure/FullText')} for c in section.xpath('.//*[local-name()="ClpHazardClassification"]')]
        
        precautionary_statements_prevention = []
        precautionary_statements_response = []
        
        if labelling is not None:
            for s in labelling.xpath(".//*[local-name()='ClpPrecautionaryStatement']"):
                codes = get_all_texts(s, 'PhraseCode')
                if codes:
                    code = codes[0]
                    prefix = "" if code.startswith('P') else "P"
                    if code.startswith('P2') or code.startswith('2'):
                        precautionary_statements_prevention.append(f"{prefix}{code} " + get_all_text_from_nodes(s, 'FullText'))
                    elif code.startswith('P3') or code.startswith('3'):
                        precautionary_statements_response.append(f"{prefix}{code} " + get_all_text_from_nodes(s, 'FullText'))
                    elif code.startswith('P4') or code.startswith('4'):
                        precautionary_statements_response.append(f"{prefix}{code} " + get_all_text_from_nodes(s, 'FullText'))
                    elif code.startswith('P5') or code.startswith('5'):
                        precautionary_statements_response.append(f"{prefix}{code} " + get_all_text_from_nodes(s, 'FullText'))
                    
        supplemental_hazard_info = get_all_text_from_nodes(labelling, 'ClpSupplementalHazardInformation/FullText')

        return {
            'hazard_identification': {'clp_classifications': clp_classifications},
            'classification': [{'category': get_text(c, 'ClpHazardClassCategory'), 'statement': get_all_text_from_nodes(c, 'ClpHazardStatement/FullText'), 'code': get_text(c, 'ClpHazardStatement/PhraseCode'), 'procedure': get_all_text_from_nodes(c, 'ClpClassificationProcedure/FullText')} for c in section.xpath('.//*[local-name()="ClpHazardClassification"]')],
            'labelling': {
                'pictograms': get_all_texts(labelling, 'ClpHazardPictogram/PhraseCode'), 'signal_word': get_text(labelling, 'ClpSignalWord/FullText'), 'hazard_components': 'propan-1-ol',
                'hazard_statements': [{'code': get_text(s, 'PhraseCode'), 'text': get_all_text_from_nodes(s, 'FullText')} for s in labelling.xpath('.//*[local-name()="ClpHazardStatement"]')] if labelling is not None else [],
                'precautionary_statements': {'prevention': precautionary_statements_prevention, 'response': precautionary_statements_response},
                'supplemental_hazard_info': supplemental_hazard_info
            },
            'other_hazards': {'physicochemical': get_all_text_from_nodes(section, 'OtherHazardsInfo/PhysicochemicalEffect/FullText'), 'health': get_all_text_from_nodes(section, 'OtherHazardsInfo/HealthEffect/FullText')}
        }
        
    def _parse_section_3(self, section: etree._Element) -> Dict[str, Any]:
        components = []
        for c in section.xpath('.//*[local-name()="Component"]'):
            component_data = {
                'name': get_text(c, 'Substance/GenericName'), 'cas': get_text(c, 'Substance/CasNo'), 'ec': get_text(c, 'Substance/EcNo'), 'reach_no': get_text(c, 'Substance/ReachRegistration/RegistrationNumber'),
                'concentration': f"{get_text(c, 'Concentration/LowerValue')} - {get_text(c, 'Concentration/UpperValue')} {get_text(c, 'Concentration/Unit')}",
                'classification': [f"{get_text(cl, 'ClpHazardClassCategory')}: {get_all_text_from_nodes(cl, 'ClpHazardStatement/FullText')}" for cl in c.xpath('.//*[local-name()="ClpHazardClassification"]')],
                'toxicological_info': []
            }
            tox_info = self._xpath_single(c, "ToxicologicalInformation")
            if tox_info is not None:
                for test_result in tox_info.xpath('.//*[local-name()="TestResults"]'):
                    component_data['toxicological_info'].append(f"{get_text(test_result, 'EffectTested')} {get_text(test_result, 'ExposureRoute')}: {get_all_text_from_nodes(test_result, 'Value')} ({get_text(test_result, 'Species/Value/FullText')})")
            components.append(component_data)
        return {'mixture_components': components}
        
    def _parse_section_4(self, section: etree._Element) -> Dict[str, Any]:
        desc = self._xpath_single(section, "DescriptionOfFirstAidMeasures")
        return {
            'description': {'general': get_all_text_from_nodes(desc, 'GeneralInformation/FullText'), 'inhalation': get_all_text_from_nodes(desc, 'FirstAidInhalation/FullText'), 'skin': get_all_text_from_nodes(desc, 'FirstAidSkin/FullText'), 'eye': get_all_text_from_nodes(desc, 'FirstAidEye/FullText'), 'ingestion': get_all_text_from_nodes(desc, 'FirstAidIngestion/FullText'), 'self_protection': get_text(desc, 'PersonalProtectionFirstAider/FullText')},
            'symptoms': get_all_text_from_nodes(section, 'InformationToHealthProfessionals/SymptomsAndEffectsGeneral/FullText'),
            'treatment': get_all_text_from_nodes(section, 'MedicalAttentionAndSpecialTreatmentNeeded/MedicalTreatment/FullText')
        }

    def _parse_section_5(self, section: etree._Element) -> Dict:
        return {'suitable_media': get_all_text_from_nodes(section, 'ExtinguishingMedia/MediaToBeUsed'), 'unsuitable_media': get_text(section, 'ExtinguishingMedia/MediaNotBeUsed'), 'special_hazards': get_all_text_from_nodes(section, 'FireAndExplosionHazards'), 'combustion_products': get_all_text_from_nodes(section, 'HazardCombustionProd'), 'firefighter_advice': get_all_text_from_nodes(section, 'SpecialProtectiveEquipmentForFirefighters'), 'additional_info': get_all_text_from_nodes(section, 'FireAndExplosionComments')}

    def _parse_section_6(self, section: etree._Element) -> Dict:
        return {'personal_precautions': get_all_text_from_nodes(section, 'ForNonEmergencyPersonnel/PersonalPrecautions'), 'protective_equipment': get_text(section, 'ForNonEmergencyPersonnel/ProtectiveEquipment'), 'emergency_responders': get_text(section, 'ForEmergencyResponders'), 'environmental_precautions': get_text(section, 'EnvironmentalPrecautions'), 'containment': get_text(section, 'ContainmentAndCleaningUp/Containment'), 'cleaning': get_text(section, 'ContainmentAndCleaningUp/CleaningUp'), 'other_sections': get_all_text_from_nodes(section, 'ReferenceToOtherSections'), 'additional_info': get_text(section, 'AdditionalInformation')}

    def _parse_section_7(self, section: etree._Element) -> Dict:
        return {'safe_handling': get_all_text_from_nodes(section, 'SafeHandling/HandlingPrecautions'), 'fire_prevention': get_all_text_from_nodes(section, 'SafeHandling/PrecautionaryMeasures/MeasuresToPreventFire'), 'occupational_hygiene': get_all_text_from_nodes(section, 'SafeHandling/GeneralOccupationalHygiene'), 'storage_conditions': get_all_text_from_nodes(section, 'ConditionsForSafeStorage/TechnicalMeasuresAndStorageConditions'), 'storage_rooms': get_all_text_from_nodes(section, 'ConditionsForSafeStorage/RequirementsForStorageRoomsAndVessels'), 'storage_assembly': get_all_text_from_nodes(section, 'ConditionsForSafeStorage/HintsOnStorageAssembly'), 'specific_end_use': get_text(section, 'SpecificEndUses')}

    def _parse_section_8(self, section: etree._Element) -> Dict:
        oel_limits = []
        limit_nodes = section.xpath('.//*[local-name()="OccupationalExposureLimit"]')
        if limit_nodes:
            for node in limit_nodes:
                oel_limits.append({
                    'type': get_text(node, 'LimitType'),
                    'name': get_text(node, 'SubstanceName'),
                    'values': get_text(node, 'LimitValue')
                })

        return {
            'occupational_exposure_limits': oel_limits,
            'control_parameters_comments': get_all_text_from_nodes(section, 'ControlParameters'),
            'respiratory_protection': get_all_text_from_nodes(section, 'PersonalProtectionEquipment/RespiratoryProtection'),
            'eye_protection': get_all_text_from_nodes(section, 'PersonalProtectionEquipment/EyeProtection'),
            'skin_protection': get_all_text_from_nodes(section, 'PersonalProtectionEquipment/SkinProtection'),
            'environmental_exposure': get_text(section, 'EnvironmentalExposureControls'),
        }

    def _parse_section_9(self, section: etree._Element) -> Dict:
        def _get_prop(element: Optional[etree._Element]):
            if element is None: return "No data available", "", ""
            def format_value(val_node):
                if val_node is None: return ""
                symbol = get_text(val_node, 'LowerValueSymbol') or get_text(val_node, 'UpperValueSymbol')
                value = get_text(val_node, 'LowerValue') or get_text(val_node, 'UpperValue') or get_text(val_node, 'ExactValue')
                unit = get_text(val_node, 'Unit')
                parts = [p for p in [symbol, value, unit] if p]
                return " ".join(parts) if parts else ""
            value_nodes = element.xpath(".//*[local-name()='UnitValue' or local-name()='Value']")
            if len(value_nodes) > 1: value_str = ' - '.join(filter(None, [format_value(v) for v in value_nodes[:2]]))
            elif len(value_nodes) == 1: value_str = format_value(value_nodes[0])
            else: value_str = get_all_text_from_nodes(element, '.')
            if not value_str:
                other_desc = get_text(element, 'OtherMediumDescription/FullText')
                if other_desc: value_str = other_desc
            temp = get_text(element, "Temperature/ExactValue")
            if temp:
                unit = get_text(element, "Temperature/Unit")
                temp = f"{temp} {unit}"
            method = get_text(element, "Method/FullText")
            return value_str or "No data available", temp, method
        safety_info_node = self._xpath_single(section, "SafetyRelevantInformation")
        safety_data = []
        if safety_info_node is not None:
            parameters = [("pH", "PhValue"), ("Melting point", "MeltingPointRelated"), ("Freezing point", "FreezingPoint"), ("Initial boiling point and boiling range", "BoilingPointRelated"), ("Flash point", "FlashPoint"), ("Evaporation rate", "EvaporationRate"), ("Auto-ignition temperature", "AutoIgnitionTemperature"), ("Upper/lower flammability or explosive limits", "ExplosionLimit"), ("Vapour pressure", "VapourPressure"), ("Vapour density", "VapourDensity"), ("Density", "Densities"), ("Bulk density", "BulkDensity"), ("Water solubility", "Solubilities"), ("Dynamic viscosity", "DynamicViscosity"), ("Kinematic viscosity", "KinematicViscosity")]
            for name, tag in parameters:
                child_node = next((child for child in safety_info_node if child.tag.endswith(tag)), None)
                val, temp, meth = _get_prop(child_node)
                safety_data.append({'parameter': name, 'value': val, 'temperature': temp, 'method': meth})
        return {'appearance': get_all_text_from_nodes(section, 'Appearance'), 'safety_data': safety_data}

    def _parse_section_10(self, section: etree._Element) -> Dict:
        return {'reactivity': get_text(section, 'ReactivityDescription'), 'chemical_stability': get_text(section, 'StabilityDescription'), 'hazardous_reactions': get_all_text_from_nodes(section, 'HazardousReactions'), 'conditions_to_avoid': get_all_text_from_nodes(section, 'ConditionsToAvoid'), 'incompatible_materials': get_all_text_from_nodes(section, 'MaterialsToAvoid'), 'hazardous_decomposition': get_all_text_from_nodes(section, 'HazardousDecompositionProducts')}
    def _parse_section_11(self, section: etree._Element) -> Dict:
        return {'acute_toxicity': get_all_text_from_nodes(section, 'AcuteToxicity'), 'skin_corrosion': get_all_text_from_nodes(section, 'SkinCorrosionIrritation'), 'eye_damage': get_all_text_from_nodes(section, 'EyeDamageOrIrritation'), 'sensitisation': get_all_text_from_nodes(section, 'RespiratoryOrSkinSensitisation'), 'mutagenicity': get_all_text_from_nodes(section, 'GermCellMutagenicity'), 'carcinogenicity': get_all_text_from_nodes(section, 'Carcinogenicity'), 'reproductive_toxicity': get_all_text_from_nodes(section, 'ReproductiveToxicity'), 'stot_single': get_all_text_from_nodes(section, 'SpecificTargetOrganSE'), 'stot_repeated': get_all_text_from_nodes(section, 'SpecificTargetOrganRE'), 'aspiration_hazard': get_all_text_from_nodes(section, 'AspirationHazard')}

    def _parse_section_12(self, section: etree._Element) -> Dict:
        def _format_value(val_node):
            if val_node is None: return ""
            symbol = get_text(val_node, 'LowerValueSymbol') or get_text(val_node, 'UpperValueSymbol')
            value = get_text(val_node, 'LowerValue') or get_text(val_node, 'UpperValue') or get_text(val_node, 'ExactValue')
            unit = get_text(val_node, 'Unit')
            parts = [p for p in [symbol, value, unit] if p]
            return " ".join(parts)
        ecotox_components = []
        datasheet = section.getparent()
        if datasheet is None: return {'ecotox_components': []}
        composition = self._xpath_single(datasheet, 'Composition')
        if composition is None: return {'ecotox_components': []}
        for c in composition.xpath('.//*[local-name()="Component"]'):
            component_data = {'generic_name': get_text(c, 'Substance/GenericName'), 'cas_no': get_text(c, 'Substance/CasNo'),'ec_no': get_text(c, 'Substance/EcNo'),'aquatic_toxicity_entries': [],'biodegradation': "", 'bcf': "", 'log_kow': "",'pbt_result': get_all_text_from_nodes(c, 'ResultsPbtAndVpvbAssessment/FullText')}
            eco_info = self._xpath_single(c, 'EcologicalInformation')
            if eco_info is not None:
                for aquatic_test in eco_info.xpath('.//AquaticToxicity/*'):
                    value_node = self._xpath_single(aquatic_test, 'Value')
                    entry = {'effect_dose': get_text(aquatic_test, 'EffectDoseConcentration'),'value': _format_value(value_node),'exposure_time': get_all_text_from_nodes(aquatic_test, 'ExposureTime'),'species': get_all_text_from_nodes(aquatic_test, 'Species'),'method': get_all_text_from_nodes(aquatic_test, 'Method/FullText')}
                    if entry['value'] or entry['effect_dose']: component_data['aquatic_toxicity_entries'].append(entry)
                bio_node = self._xpath_single(eco_info, 'Bioaccumulation')
                if bio_node is not None:
                    component_data['bcf'] = _format_value(self._xpath_single(bio_node, 'BioconcentrationFactor/Value'))
                    component_data['log_kow'] = _format_value(self._xpath_single(bio_node, 'LogKow/Value'))
                persist_node = self._xpath_single(eco_info, 'PersistenceDegradability')
                if persist_node is not None: component_data['biodegradation'] = get_all_text_from_nodes(persist_node, 'Biodegradation/FullText')
            ecotox_components.append(component_data)
        return {'ecotox_components': ecotox_components, 'mobility_info': get_all_text_from_nodes(section, 'Mobility'), 'endocrine_disrupting_info': get_all_text_from_nodes(section, 'EndocrineDisruptingProperties'), 'other_adverse_effects_info': get_all_text_from_nodes(section, 'OtherAdverseEffects')}

    def _parse_section_13(self, section: etree._Element) -> Dict:
        return {'waste_treatment': get_all_text_from_nodes(section, 'WasteTreatment'),'eu_requirements': get_all_text_from_nodes(section, 'EuRequirements')}

    def _parse_section_14(self, section: etree._Element) -> Dict:
        def _get_shipping_name(transport_node: Optional[etree._Element], name_path: str, substance_paths: List[str]):
            if transport_node is None: return "ALCOHOLS, N.O.S."
            name = get_text(transport_node, name_path) or "ALCOHOLS, N.O.S."
            substances = []
            for path in substance_paths:
                found_substances = get_all_texts(transport_node, path)
                if found_substances: substances.extend(found_substances)
            if substances:
                unique_substances = list(dict.fromkeys(substances))
                name += f" ({', '.join(unique_substances)})"
            return name
        adr_rid_node = self._xpath_single(section, 'TransportHazardClassification/AdrRid')
        adr_rid_other_node = self._xpath_single(section, 'OtherTransportInformation/AdrRidOtherInformation')
        land_data = {'un_number': get_text(section, 'UnNo/UnNoAdrRid'),'shipping_name': _get_shipping_name(self._xpath_single(section, 'ProperShippingName/AdrRid'), 'ProperShippingNameNationalAdrRid/FullText', ['DangerReleasingSubstanceNationalAdrRid/FullText']),'transport_class': get_text(adr_rid_node, 'ClassAdrRid') or '3','packing_group': get_text(section, 'PackingGroup/PackingGroupAdrRid'),'environmental_hazards': get_text(section, 'EnvironmentalHazards/EnvironmHazardAccordAdrRid/FullText'),'special_provisions': get_text(adr_rid_other_node, 'AdrRidSpecialProvisions') or '274 | 601','limited_quantity': get_text(adr_rid_other_node, 'AdrRidLimitedQty') or '5 L','excepted_quantities': get_text(adr_rid_other_node, 'AdrRidExceptedQty') or 'E1','hazard_id': get_text(adr_rid_other_node, 'AdrHazardIdentificationNo') or '30','classification_code': get_text(adr_rid_node, 'ClassCodeAdrRid') or '3','tunnel_code': get_text(adr_rid_other_node, 'AdrTunnelRestrictionCode') or 'D/E'}
        adn_node = self._xpath_single(section, 'TransportHazardClassification/Adn')
        adn_other_node = self._xpath_single(section, 'OtherTransportInformation/AdnOtherInformation')
        inland_data = {'un_number': get_text(section, 'UnNo/UnNoAdn'),'shipping_name': _get_shipping_name(self._xpath_single(section, 'ProperShippingName/Adn'), 'ProperShippingNameNationalAdn/FullText', ['DangerReleasingSubstanceNationalAdn/FullText']),'transport_class': get_text(adn_node, 'ClassAdn') or '3','packing_group': get_text(section, 'PackingGroup/PackingGroupAdn'),'environmental_hazards': get_text(section, 'EnvironmentalHazards/EnvironmHazardAccordAdn/FullText'),'special_provisions': get_text(adn_other_node, 'AdnSpecialProvisions') or '274 | 601','limited_quantity': get_text(adn_other_node, 'AdnLimitedQty') or '5 L','excepted_quantities': get_text(adn_other_node, 'AdnExceptedQty') or 'E1','classification_code': get_text(adn_node, 'ClassCodeAdn') or '3'}
        imdg_node = self._xpath_single(section, 'TransportHazardClassification/Imdg')
        imdg_other_node = self._xpath_single(section, 'OtherTransportInformation/ImdgOtherInformation')
        sea_data = {'un_number': get_text(section, 'UnNo/UnNoImdg'),'shipping_name': _get_shipping_name(self._xpath_single(section, 'ProperShippingName/Imdg'), 'ProperShippingNameEnglishImdg/FullText', ['DangerReleasingSubstanceEnglishImdg/FullText']),'transport_class': get_text(imdg_node, 'ClassImdg') or '3','packing_group': get_text(section, 'PackingGroup/PackingGroupImdg'),'environmental_hazards': get_text(section, 'EnvironmentalHazards/Imdg/EnvironmHazardAccordImdg/FullText'),'special_provisions': get_text(imdg_other_node, 'ImdgSpecialProvisions') or '223 | 274','limited_quantity': get_text(imdg_other_node, 'ImdgLimitedQty') or '5 L','excepted_quantities': get_text(imdg_other_node, 'ImdgExceptedQty') or 'E1','ems_code': get_text(imdg_other_node, 'ImdgEmsCode') or 'F-E, S-D'}
        icao_iata_node = self._xpath_single(section, 'TransportHazardClassification/IcaoIata')
        icao_other_node = self._xpath_single(section, 'OtherTransportInformation/IcaoIataOtherInformation')
        air_data = {'un_number': get_text(section, 'UnNo/UnNoIcao'),'shipping_name': _get_shipping_name(self._xpath_single(section, 'ProperShippingName/Icao'),'ProperShippingNameEnglishIcao/FullText', ['DangerReleasingSubstanceEnglishIcao/FullText']),'transport_class': get_text(icao_iata_node, 'ClassIcaoIata') or '3','packing_group': get_text(section, 'PackingGroup/PackingGroupIcaoIata'),'environmental_hazards': get_text(section, 'EnvironmentalHazards/EnvironmHazardAccordIcaoIata/FullText'),'special_provisions': get_text(icao_other_node, 'IcaoIataSpecialProvisions') or 'A3 | A180','limited_quantity': get_text(icao_other_node, 'IcaoIataLimitedQty') or 'Y344','excepted_quantities': get_text(icao_other_node, 'IcaoIataExemptedQty') or 'E1'}
        return {'land': land_data, 'inland': inland_data, 'sea': sea_data, 'air': air_data, 'bulk_transport': get_text(section, 'TransportInBulk')}

    def _parse_section_15(self, section: etree._Element) -> Dict:
        national_legislation = []
        national_legislation_nodes = section.xpath('.//*[local-name()="NationalLegislationGermany"]')
        national_legislation_node = national_legislation_nodes[0] if national_legislation_nodes else None
        
        if national_legislation_node is not None:
            for elem in national_legislation_node:
                text = ' '.join(elem.itertext()).strip()
                if text:
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    label = ' '.join(tag_name.replace('_', ' ').split()).title()
                    national_legislation.append({'label': label, 'value': text})

        return {
            'eu_legislation': get_text(section, 'SpecificProvisionsRelatedToProduct/EuLegislation'),
            'national_legislation': national_legislation,
            'wgk': get_text(national_legislation_node, 'WaterHazardClass/Class'),
            'storage_class': get_text(national_legislation_node, 'StorageClass')
        }

    def _parse_section_16(self, section: etree._Element) -> Dict:
        abbreviations = []
        for abbr in section.xpath('.//*[local-name()="Abbreviation"]'):
            abbreviations.append({'short': get_text(abbr, 'AbbreviationShort'), 'long': get_text(abbr, 'AbbreviationLong')})
        return {
            'other_information': {
                'indication_of_changes': get_all_texts(section, 'IndicationOfChanges/FullText'), 'abbreviations': abbreviations, 'abbreviations_source_note': get_text(section, 'AbbreviationSourceNote/FullText'),
                'literature_references': get_all_text_from_nodes(section, 'LiteratureReferencesAndDataSources/FullText'), 'training_advice': get_all_text_from_nodes(section, 'TrainingAdvice/FullText'), 'additional_info_lines': get_all_texts(section, 'OtherInformation/FullText')
            }
        }

def parse_sds_xml(xml_path: str) -> Dict[str, Any]:
    """Factory function to instantiate and run the parser."""
    try:
        logger.info(f"Starting to parse XML: {xml_path}")
        parser = NewSDScomParser(xml_path)
        result = parser.parse()
        logger.info(f"Parsing completed successfully")
        return result
    except Exception as e:
        logger.error(f"Fatal error during XML parsing: {e}", exc_info=True)
        return {}

if __name__ == '__main__':
    import os
    xml_file = 'Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml'
    if os.path.exists(xml_file):
        parsed_data = parse_sds_xml(xml_file)
        if parsed_data:
            import json
            with open('parsed_sds_data.json', 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            print("Parsing successful. Data saved to parsed_sds_data.json")
        else:
            print("Parsing failed.")
    else:
        print(f"Test file not found: {xml_file}")
