# Requirements: SDS Hybrid Parser & Validator System

## 1. Overview

### 1.1 Purpose
Implement a two-stage system that ensures complete and accurate Safety Data Sheet (SDS) data extraction before translation:
1. **Stage 1**: Hybrid Parser with PDF Fallback - Extract data from XML first, then fill gaps from PDF
2. **Stage 2**: XML Validator & Gap Report - Verify completeness and identify any remaining gaps

### 1.2 Background
Current analysis shows that the XML file (`Sdb_EU-REACH_MycoplasmaOff™_15-5000,15-1000,15-0050_V5_en_DE.xml`) is missing critical data in several sections:
- **Section 8**: Occupational Exposure Limits (currently hardcoded)
- **Section 12**: Mobility, endocrine disrupting properties, other adverse effects
- **Section 15**: EU legislation details
- **Section 16**: Completely empty (abbreviations, literature references, classification details)

### 1.3 Goals
- Achieve 100% data completeness before translation
- Eliminate hardcoded data in parsers
- Provide transparency about data sources (XML vs PDF)
- Enable quality assurance through gap reporting

---

## 2. Functional Requirements

### 2.1 Stage 1: Hybrid Parser with PDF Fallback

#### FR-1.1: XML-First Parsing
**Priority**: High  
**Description**: Parse all 16 SDS sections from XML file as primary data source

**Acceptance Criteria**:
- All existing XML data is extracted correctly
- Parser uses existing `sds_parser.py` (NewSDScomParser) as foundation
- No data loss compared to current implementation
- Maintains backward compatibility with existing templates

#### FR-1.2: Gap Detection
**Priority**: High  
**Description**: Automatically detect missing or empty fields in XML data

**Acceptance Criteria**:
- System identifies empty XML tags (e.g., `<OtherInformation/>`)
- System detects missing required fields per section
- Gap detection covers all 16 sections
- Returns structured list of missing fields with section numbers

**Known Gaps to Detect**:
- Section 1.2: Life Cycle Stage (LCS)
- Section 8.1: Occupational Exposure Limit Values table
- Section 12: Mobility, Endocrine disrupting properties, Other adverse effects
- Section 15.1: EU Legislation text
- Section 15.2: National regulations details (JArbSchG, MuSchRiV, BetrSichV, Störfallverordnung)
- Section 16: All subsections (completely empty)

#### FR-1.3: PDF Fallback Extraction
**Priority**: High  
**Description**: Extract missing data from PDF file for identified gaps

**Acceptance Criteria**:
- PDF parser targets only missing fields (not entire document)
- Extraction is section-specific and field-specific
- PDF data is structured to match XML data format
- System handles PDF parsing errors gracefully

**PDF Extraction Targets**:
1. **Section 1.2**: Extract "Life cycle stage [LCS]" value
2. **Section 8.1**: Extract occupational exposure limits table
3. **Section 12**: Extract mobility, endocrine disrupting, other adverse effects text
4. **Section 15.1**: Extract EU legislation paragraph
5. **Section 15.2**: Extract national regulations list
6. **Section 16**: Extract all subsections:
   - Indication of changes
   - Abbreviations and acronyms table
   - Key literature references
   - Classification for mixtures table
   - List of relevant hazard statements
   - Training advice
   - Additional information

#### FR-1.4: Data Merging
**Priority**: High  
**Description**: Merge XML and PDF data with clear prioritization

**Acceptance Criteria**:
- XML data always takes precedence when present
- PDF data fills only detected gaps
- Merged data structure is identical to pure XML structure
- Each field tracks its source (XML or PDF) for transparency

#### FR-1.5: Source Tracking
**Priority**: Medium  
**Description**: Track data source for each field (XML vs PDF)

**Acceptance Criteria**:
- Metadata indicates source for each extracted field
- Source information is available for debugging/validation
- Optional: Include source info in rendered output (for QA)

---

### 2.2 Stage 2: XML Validator & Gap Report

#### FR-2.1: Completeness Validation
**Priority**: High  
**Description**: Validate that all required SDS fields are present after hybrid parsing

**Acceptance Criteria**:
- Validates all 16 sections against SDS requirements
- Checks for empty or missing required fields
- Returns validation status (PASS/FAIL) per section
- Provides overall completeness percentage

**Required Fields per Section**:
- Section 1: Product identifier, Relevant uses, Supplier details, Emergency phone
- Section 2: Classification, Label elements, Other hazards
- Section 3: Mixture components with CAS/EC numbers, concentrations
- Section 4: First aid measures (all routes)
- Section 5: Firefighting measures
- Section 6: Accidental release measures
- Section 7: Handling and storage
- Section 8: Exposure controls, Personal protection
- Section 9: Physical and chemical properties
- Section 10: Stability and reactivity
- Section 11: Toxicological information
- Section 12: Ecological information
- Section 13: Disposal considerations
- Section 14: Transport information
- Section 15: Regulatory information
- Section 16: Other information

#### FR-2.2: Gap Report Generation
**Priority**: High  
**Description**: Generate detailed report of any remaining gaps after hybrid parsing

**Acceptance Criteria**:
- Report lists all missing fields by section
- Report indicates severity (Critical, Warning, Info)
- Report includes recommendations for resolution
- Report is human-readable and machine-parseable (JSON + Markdown)

**Gap Severity Levels**:
- **Critical**: Required field missing, blocks translation
- **Warning**: Recommended field missing, translation possible but incomplete
- **Info**: Optional field missing, no impact on translation

#### FR-2.3: Pre-Translation Gate
**Priority**: High  
**Description**: Block translation process if critical gaps remain

**Acceptance Criteria**:
- System prevents translation if critical gaps exist
- Clear error message indicates which fields are missing
- User can override with explicit confirmation (for testing)
- Successful validation allows translation to proceed

#### FR-2.4: Quality Metrics
**Priority**: Medium  
**Description**: Provide quality metrics for parsed data

**Acceptance Criteria**:
- Overall completeness percentage (0-100%)
- Completeness per section (0-100%)
- Count of fields: Total, Present, Missing
- Data source breakdown (% from XML, % from PDF)

---

## 3. Non-Functional Requirements

### NFR-1: Performance
- Hybrid parsing should complete within 10 seconds for typical SDS file
- PDF extraction should be optimized (extract only needed sections)
- Validation should complete within 2 seconds

### NFR-2: Reliability
- System handles malformed XML gracefully
- System handles PDF parsing errors without crashing
- Fallback to XML-only mode if PDF unavailable

### NFR-3: Maintainability
- Clear separation between XML parser, PDF parser, and merger
- Modular design allows easy addition of new gap detection rules
- Comprehensive logging for debugging

### NFR-4: Compatibility
- Works with existing Flask application
- Compatible with current template system
- No breaking changes to existing API

---

## 4. User Stories

### US-1: Complete Data Extraction
**As a** SDS translator  
**I want** all SDS data extracted completely from XML and PDF  
**So that** translations are accurate and complete

**Acceptance Criteria**:
- All 16 sections have complete data
- No hardcoded values in parser
- Data source is transparent

### US-2: Gap Visibility
**As a** quality assurance specialist  
**I want** to see which data came from XML vs PDF  
**So that** I can verify data quality and identify XML improvements

**Acceptance Criteria**:
- Gap report shows all missing XML fields
- Report indicates which fields were filled from PDF
- Report is generated before translation

### US-3: Translation Confidence
**As a** system administrator  
**I want** validation before translation starts  
**So that** I know the translation will be complete

**Acceptance Criteria**:
- Validation runs automatically before translation
- Critical gaps block translation
- Clear feedback on data completeness

---

## 5. Technical Constraints

### TC-1: Existing Codebase
- Must integrate with existing `sds_parser.py` (NewSDScomParser)
- Must work with existing `sds_xml_importer.py`
- Must support existing Jinja2 templates

### TC-2: File Formats
- XML: SDScom format (namespace-agnostic parsing required)
- PDF: Standard PDF format (may require OCR for scanned documents)

### TC-3: Dependencies
- Python 3.x
- lxml for XML parsing
- PyPDF2 or pdfplumber for PDF extraction
- Existing Flask application framework

---

## 6. Out of Scope

The following are explicitly out of scope for this feature:

- Translation functionality (already exists)
- PDF generation (already exists)
- Database storage of parsed data
- Web UI for gap report (CLI/API only)
- Automatic correction of XML files
- Support for non-SDScom XML formats

---

## 7. Success Criteria

The feature is considered successful when:

1. ✅ All identified gaps in XML are filled from PDF
2. ✅ No hardcoded data remains in parsers
3. ✅ Validation report shows 100% completeness for test SDS
4. ✅ Translation process uses hybrid parser automatically
5. ✅ Gap report is generated and accessible
6. ✅ System handles errors gracefully without crashes

---

## 8. Dependencies

### Internal Dependencies
- `sds_parser.py` - Current XML parser
- `sds_xml_importer.py` - Current importer
- `layout-placeholders-fixed-v2.html` - Jinja2 template
- Flask application (`app.py`)

### External Dependencies
- PDF parsing library (to be selected: PyPDF2, pdfplumber, or pymupdf)
- Existing lxml library for XML parsing

---

## 9. Risks and Mitigations

### Risk 1: PDF Parsing Accuracy
**Risk**: PDF text extraction may be inaccurate or incomplete  
**Mitigation**: 
- Use multiple PDF parsing libraries as fallback
- Implement validation of extracted PDF data
- Allow manual override/correction

### Risk 2: Performance Impact
**Risk**: PDF parsing may slow down the system significantly  
**Mitigation**:
- Cache PDF extraction results
- Extract only needed sections (not entire PDF)
- Implement async processing for large files

### Risk 3: XML Format Changes
**Risk**: Future XML format changes may break gap detection  
**Mitigation**:
- Make gap detection rules configurable
- Implement comprehensive logging
- Add unit tests for gap detection

---

## 10. Future Enhancements

Potential future improvements (not in current scope):

1. **Machine Learning Gap Filling**: Use ML to predict missing values
2. **Multi-PDF Support**: Extract from multiple PDF versions
3. **XML Enhancement Tool**: Automatically improve XML files
4. **Real-time Validation UI**: Web interface for gap report
5. **Batch Processing**: Process multiple SDS files in parallel
6. **API Endpoints**: RESTful API for hybrid parsing and validation

---

## 11. Acceptance Criteria Summary

The feature is ready for production when:

- [ ] All functional requirements (FR-1.1 to FR-2.4) are implemented
- [ ] All non-functional requirements (NFR-1 to NFR-4) are met
- [ ] All user stories (US-1 to US-3) are satisfied
- [ ] Test SDS file achieves 100% completeness
- [ ] Gap report is generated successfully
- [ ] No hardcoded data remains in parsers
- [ ] Integration tests pass
- [ ] Documentation is complete
