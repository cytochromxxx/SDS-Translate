# Design: SDS Hybrid Parser & Validator System

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SDS Processing Pipeline                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Hybrid Parser with PDF Fallback                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ XML Parser   │→ │ Gap Detector │→ │ PDF Fallback │         │
│  │ (Primary)    │  │              │  │ (Secondary)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                              │                                   │
│                              ▼                                   │
│                    ┌──────────────┐                             │
│                    │ Data Merger  │                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Validator & Gap Report                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Completeness │→ │ Gap Report   │→ │ Pre-Trans    │         │
│  │ Validator    │  │ Generator    │  │ Gate         │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Translation      │
                    │ (Existing)       │
                    └──────────────────┘
```

### 1.2 Component Overview

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **XMLParser** | Parse XML file | XML file path | Structured data dict |
| **GapDetector** | Identify missing fields | Parsed XML data | List of gaps |
| **PDFExtractor** | Extract missing data from PDF | PDF path + gap list | Extracted data dict |
| **DataMerger** | Merge XML + PDF data | XML data + PDF data | Complete data dict |
| **Validator** | Validate completeness | Merged data | Validation result |
| **GapReporter** | Generate gap report | Validation result | Report (JSON/MD) |
| **PreTransGate** | Block/allow translation | Validation result | Boolean + message |

---

## 2. Detailed Component Design

### 2.1 Stage 1: Hybrid Parser

#### 2.1.1 XMLParser (Enhanced)

**File**: `sds_hybrid_parser.py`

**Class**: `HybridSDSParser`

**Purpose**: Extends existing `NewSDScomParser` with gap detection

**Key Methods**:
```python
class HybridSDSParser(NewSDScomParser):
    def parse_with_gap_detection(self, xml_path: str) -> Tuple[Dict, List[Gap]]:
        """Parse XML and detect gaps simultaneously"""
        
    def _detect_gaps_in_section(self, section_num: int, section_data: Dict) -> List[Gap]:
        """Detect missing fields in a specific section"""
        
    def _is_field_empty(self, value: Any) -> bool:
        """Check if a field is empty/missing"""
```

**Gap Detection Rules**:
```python
REQUIRED_FIELDS = {
    1: ['product_identifier.trade_name', 'supplier_details.name', 'emergency_phone.number'],
    2: ['classification', 'labelling.pictograms', 'labelling.signal_word'],
    3: ['mixture_components'],
    # ... for all 16 sections
    8: ['occupational_exposure_limits'],  # Currently missing!
    15: ['eu_legislation'],  # Currently missing!
    16: ['abbreviations', 'literature_references', 'clp_classifications']  # All missing!
}
```

#### 2.1.2 GapDetector

**File**: `gap_detector.py`

**Class**: `SDSGapDetector`

**Purpose**: Identify missing or empty fields in parsed data

**Data Structure**:
```python
@dataclass
class Gap:
    section: int
    subsection: str
    field_path: str
    severity: str  # 'critical', 'warning', 'info'
    description: str
    expected_type: str  # 'text', 'table', 'list'
```

**Key Methods**:
```python
class SDSGapDetector:
    def detect_gaps(self, parsed_data: Dict) -> List[Gap]:
        """Detect all gaps in parsed data"""
        
    def _check_section(self, section_num: int, section_data: Dict) -> List[Gap]:
        """Check specific section for gaps"""
        
    def _is_critical_gap(self, section: int, field: str) -> bool:
        """Determine if gap is critical"""
```

**Known Gaps Configuration**:
```python
KNOWN_GAPS = {
    'section_1': {
        'relevant_uses.lcs': {
            'severity': 'warning',
            'pdf_location': 'Section 1.2, Life cycle stage [LCS]',
            'expected_format': 'text'
        }
    },
    'section_8': {
        'occupational_exposure_limits': {
            'severity': 'critical',
            'pdf_location': 'Section 8.1.1, Occupational exposure limit values table',
            'expected_format': 'table'
        }
    },
    'section_16': {
        'other_information.abbreviations': {
            'severity': 'critical',
            'pdf_location': 'Section 16.2, Abbreviations and acronyms',
            'expected_format': 'table'
        }
    }
}
```

#### 2.1.3 PDFExtractor

**File**: `pdf_gap_extractor.py`

**Class**: `SDSPDFGapExtractor`

**Purpose**: Extract only missing data from PDF (not entire document)

**Key Methods**:
```python
class SDSPDFGapExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_reader = self._init_pdf_reader()
        
    def extract_gaps(self, gaps: List[Gap]) -> Dict[str, Any]:
        """Extract data for specific gaps from PDF"""
        
    def _extract_section_1_lcs(self) -> str:
        """Extract Life Cycle Stage from Section 1.2"""
        
    def _extract_section_8_oel_table(self) -> List[Dict]:
        """Extract Occupational Exposure Limits table from Section 8.1"""
        
    def _extract_section_16_abbreviations(self) -> List[Dict]:
        """Extract abbreviations table from Section 16.2"""
        
    def _extract_section_16_all(self) -> Dict:
        """Extract all Section 16 data (completely missing in XML)"""
```

**PDF Extraction Strategy**:
```python
# Section-specific extraction patterns
EXTRACTION_PATTERNS = {
    'section_1_lcs': {
        'page': 1,
        'search_text': 'Life cycle stage [LCS]',
        'extract_method': 'text_after_label',
        'pattern': r'Life cycle stage \[LCS\]\s+(.+?)(?:\n|Sector)'
    },
    'section_8_oel': {
        'page': 4,
        'search_text': 'Occupational exposure limit values',
        'extract_method': 'table_extraction',
        'table_headers': ['Limit value type', 'Substance name', 'Values']
    },
    'section_16_abbreviations': {
        'page': 10,
        'search_text': 'Abbreviations and acronyms',
        'extract_method': 'table_extraction',
        'table_headers': ['Abbreviation', 'Full text']
    }
}
```

**PDF Library Selection**:
- **Primary**: `pdfplumber` (best for tables)
- **Fallback**: `PyPDF2` (simple text extraction)
- **OCR Fallback**: `pytesseract` (for scanned PDFs)

#### 2.1.4 DataMerger

**File**: `data_merger.py`

**Class**: `SDSDataMerger`

**Purpose**: Merge XML and PDF data with source tracking

**Key Methods**:
```python
class SDSDataMerger:
    def merge(self, xml_data: Dict, pdf_data: Dict, gaps: List[Gap]) -> MergedData:
        """Merge XML and PDF data, XML takes precedence"""
        
    def _merge_field(self, xml_value: Any, pdf_value: Any, field_path: str) -> FieldValue:
        """Merge single field with source tracking"""
        
    def _track_source(self, field_path: str, source: str):
        """Track data source for transparency"""
```

**Data Structure**:
```python
@dataclass
class FieldValue:
    value: Any
    source: str  # 'xml', 'pdf', 'merged'
    confidence: float  # 0.0-1.0
    
@dataclass
class MergedData:
    data: Dict[str, Any]
    metadata: Dict[str, FieldValue]
    merge_summary: Dict[str, int]  # {'xml': 150, 'pdf': 12, 'missing': 3}
```

**Merge Priority Rules**:
1. If XML field exists and not empty → Use XML
2. If XML field missing/empty and PDF available → Use PDF
3. If both missing → Mark as gap in validation
4. Track source for every field

---

### 2.2 Stage 2: Validator & Gap Report

#### 2.2.1 Completeness Validator

**File**: `sds_validator.py`

**Class**: `SDSCompletenessValidator`

**Purpose**: Validate that all required fields are present

**Key Methods**:
```python
class SDSCompletenessValidator:
    def validate(self, merged_data: MergedData) -> ValidationResult:
        """Validate completeness of merged data"""
        
    def _validate_section(self, section_num: int, section_data: Dict) -> SectionValidation:
        """Validate specific section"""
        
    def _calculate_completeness(self, validation: ValidationResult) -> float:
        """Calculate overall completeness percentage"""
```

**Validation Rules**:
```python
VALIDATION_RULES = {
    'section_1': {
        'required': ['product_identifier', 'supplier_details', 'emergency_phone'],
        'recommended': ['relevant_uses.lcs'],
        'optional': []
    },
    'section_8': {
        'required': ['occupational_exposure_limits', 'eye_protection', 'skin_protection'],
        'recommended': ['respiratory_protection'],
        'optional': ['environmental_exposure']
    },
    # ... for all 16 sections
}
```

**Data Structures**:
```python
@dataclass
class SectionValidation:
    section_num: int
    status: str  # 'pass', 'warning', 'fail'
    completeness: float  # 0.0-1.0
    missing_required: List[str]
    missing_recommended: List[str]
    
@dataclass
class ValidationResult:
    overall_status: str  # 'pass', 'warning', 'fail'
    overall_completeness: float
    section_validations: Dict[int, SectionValidation]
    critical_gaps: List[Gap]
    warnings: List[Gap]
```

#### 2.2.2 Gap Report Generator

**File**: `gap_reporter.py`

**Class**: `SDSGapReporter`

**Purpose**: Generate human-readable and machine-parseable gap reports

**Key Methods**:
```python
class SDSGapReporter:
    def generate_report(self, validation: ValidationResult, merged_data: MergedData) -> GapReport:
        """Generate comprehensive gap report"""
        
    def export_json(self, report: GapReport, output_path: str):
        """Export report as JSON"""
        
    def export_markdown(self, report: GapReport, output_path: str):
        """Export report as Markdown"""
        
    def export_html(self, report: GapReport, output_path: str):
        """Export report as HTML"""
```

**Report Structure**:
```python
@dataclass
class GapReport:
    timestamp: datetime
    sds_file: str
    overall_completeness: float
    status: str
    summary: ReportSummary
    sections: List[SectionReport]
    recommendations: List[str]
    
@dataclass
class ReportSummary:
    total_fields: int
    present_fields: int
    missing_fields: int
    xml_fields: int
    pdf_fields: int
    critical_gaps: int
    warnings: int
    
@dataclass
class SectionReport:
    section_num: int
    section_name: str
    completeness: float
    status: str
    gaps: List[Gap]
    data_sources: Dict[str, str]  # field -> source
```

**Report Formats**:

**JSON Format**:
```json
{
  "timestamp": "2024-03-12T10:30:00Z",
  "sds_file": "Mycoplasma_Off.xml",
  "overall_completeness": 0.92,
  "status": "warning",
  "summary": {
    "total_fields": 165,
    "present_fields": 152,
    "missing_fields": 13,
    "xml_fields": 140,
    "pdf_fields": 12,
    "critical_gaps": 0,
    "warnings": 3
  },
  "sections": [...]
}
```

**Markdown Format**:
```markdown
# SDS Gap Report

**File**: Mycoplasma_Off.xml  
**Generated**: 2024-03-12 10:30:00  
**Overall Completeness**: 92%  
**Status**: ⚠️ WARNING

## Summary
- Total Fields: 165
- Present: 152 (92%)
- Missing: 13 (8%)
- From XML: 140 (85%)
- From PDF: 12 (7%)

## Section Details
### ✅ Section 1: Identification (95%)
- ⚠️ Missing: Life Cycle Stage (filled from PDF)

### ❌ Section 16: Other Information (0%)
- 🔴 Critical: All fields missing
- Extracted from PDF: Abbreviations, Literature references
```

#### 2.2.3 Pre-Translation Gate

**File**: `pre_translation_gate.py`

**Class**: `PreTranslationGate`

**Purpose**: Block translation if critical gaps exist

**Key Methods**:
```python
class PreTranslationGate:
    def check(self, validation: ValidationResult) -> GateResult:
        """Check if translation can proceed"""
        
    def _has_critical_gaps(self, validation: ValidationResult) -> bool:
        """Check for critical gaps"""
        
    def _generate_error_message(self, critical_gaps: List[Gap]) -> str:
        """Generate user-friendly error message"""
```

**Gate Logic**:
```python
def check(self, validation: ValidationResult) -> GateResult:
    if validation.overall_status == 'fail':
        return GateResult(
            allowed=False,
            message="Translation blocked: Critical gaps detected",
            critical_gaps=validation.critical_gaps
        )
    elif validation.overall_status == 'warning':
        return GateResult(
            allowed=True,
            message="Translation allowed with warnings",
            warnings=validation.warnings
        )
    else:
        return GateResult(
            allowed=True,
            message="Translation allowed: All checks passed"
        )
```

---

## 3. Data Flow

### 3.1 Complete Processing Flow

```python
# Step 1: Parse XML with gap detection
hybrid_parser = HybridSDSParser(xml_path)
xml_data, detected_gaps = hybrid_parser.parse_with_gap_detection()

# Step 2: Extract missing data from PDF
pdf_extractor = SDSPDFGapExtractor(pdf_path)
pdf_data = pdf_extractor.extract_gaps(detected_gaps)

# Step 3: Merge XML and PDF data
merger = SDSDataMerger()
merged_data = merger.merge(xml_data, pdf_data, detected_gaps)

# Step 4: Validate completeness
validator = SDSCompletenessValidator()
validation_result = validator.validate(merged_data)

# Step 5: Generate gap report
reporter = SDSGapReporter()
gap_report = reporter.generate_report(validation_result, merged_data)
reporter.export_markdown(gap_report, 'gap_report.md')

# Step 6: Check pre-translation gate
gate = PreTranslationGate()
gate_result = gate.check(validation_result)

if gate_result.allowed:
    # Proceed to translation
    proceed_to_translation(merged_data.data)
else:
    # Block translation, show error
    raise TranslationBlockedError(gate_result.message)
```

### 3.2 Integration with Existing System

**Current Flow**:
```python
# app.py / routes/main.py
xml_data = parse_sds_xml(xml_path)  # sds_parser.py
html = import_sds_to_html(xml_path, template_path)  # sds_xml_importer.py
```

**New Flow**:
```python
# app.py / routes/main.py
from sds_hybrid_parser import parse_sds_hybrid
from sds_validator import validate_and_report

# Parse with hybrid approach
merged_data, gap_report = parse_sds_hybrid(xml_path, pdf_path)

# Validate before translation
validation = validate_and_report(merged_data)

if validation.allowed:
    # Use merged data for template rendering
    html = render_sds_template(merged_data.data, template_path)
else:
    # Show gap report to user
    return render_template('gap_report.html', report=gap_report)
```

---

## 4. File Structure

```
sds-hybrid-parser-validator/
├── sds_hybrid_parser.py          # Main hybrid parser
├── gap_detector.py                # Gap detection logic
├── pdf_gap_extractor.py           # PDF extraction for gaps
├── data_merger.py                 # XML + PDF merger
├── sds_validator.py               # Completeness validator
├── gap_reporter.py                # Gap report generator
├── pre_translation_gate.py        # Translation gate
├── config/
│   ├── required_fields.py         # Required fields per section
│   ├── gap_patterns.py            # Known gap patterns
│   └── pdf_extraction_rules.py    # PDF extraction rules
├── tests/
│   ├── test_hybrid_parser.py
│   ├── test_gap_detector.py
│   ├── test_pdf_extractor.py
│   ├── test_data_merger.py
│   ├── test_validator.py
│   └── test_integration.py
└── utils/
    ├── pdf_utils.py               # PDF helper functions
    └── validation_utils.py        # Validation helpers
```

---

## 5. API Design

### 5.1 Main API Function

```python
def parse_sds_hybrid(
    xml_path: str,
    pdf_path: Optional[str] = None,
    validate: bool = True,
    generate_report: bool = True
) -> Tuple[MergedData, Optional[GapReport]]:
    """
    Parse SDS with hybrid XML+PDF approach
    
    Args:
        xml_path: Path to XML file
        pdf_path: Path to PDF file (optional, for gap filling)
        validate: Run validation after parsing
        generate_report: Generate gap report
        
    Returns:
        Tuple of (merged_data, gap_report)
        
    Raises:
        XMLParsingError: If XML parsing fails
        PDFExtractionError: If PDF extraction fails
        ValidationError: If validation fails critically
    """
```

### 5.2 Validation API

```python
def validate_sds_completeness(
    data: Dict,
    strict: bool = False
) -> ValidationResult:
    """
    Validate SDS data completeness
    
    Args:
        data: Parsed SDS data
        strict: If True, warnings become errors
        
    Returns:
        ValidationResult with status and gaps
    """
```

### 5.3 Gap Report API

```python
def generate_gap_report(
    validation: ValidationResult,
    merged_data: MergedData,
    format: str = 'markdown'
) -> str:
    """
    Generate gap report in specified format
    
    Args:
        validation: Validation result
        merged_data: Merged data with metadata
        format: 'json', 'markdown', or 'html'
        
    Returns:
        Report as string
    """
```

---

## 6. Configuration

### 6.1 Required Fields Configuration

**File**: `config/required_fields.py`

```python
REQUIRED_FIELDS = {
    1: {
        'critical': [
            'product_identifier.trade_name',
            'product_identifier.item_no',
            'supplier_details.name',
            'supplier_details.address',
            'emergency_phone.number'
        ],
        'recommended': [
            'product_identifier.ufi',
            'relevant_uses.lcs',
            'relevant_uses.su',
            'relevant_uses.pc1'
        ]
    },
    # ... for all 16 sections
}
```

### 6.2 PDF Extraction Rules

**File**: `config/pdf_extraction_rules.py`

```python
PDF_EXTRACTION_RULES = {
    'section_1_lcs': {
        'page_range': (1, 1),
        'search_pattern': r'Life cycle stage \[LCS\]\s+(.+?)(?:\n|Sector)',
        'extraction_method': 'regex',
        'fallback_method': 'table_cell'
    },
    'section_8_oel': {
        'page_range': (4, 5),
        'table_identifier': 'Occupational exposure limit values',
        'extraction_method': 'table',
        'table_structure': {
            'headers': ['Limit value type', 'Substance name', 'Values'],
            'merge_cells': True
        }
    }
}
```

---

## 7. Error Handling

### 7.1 Error Hierarchy

```python
class SDSProcessingError(Exception):
    """Base exception for SDS processing"""

class XMLParsingError(SDSProcessingError):
    """XML parsing failed"""

class PDFExtractionError(SDSProcessingError):
    """PDF extraction failed"""

class GapDetectionError(SDSProcessingError):
    """Gap detection failed"""

class ValidationError(SDSProcessingError):
    """Validation failed"""

class TranslationBlockedError(SDSProcessingError):
    """Translation blocked due to critical gaps"""
```

### 7.2 Error Handling Strategy

```python
try:
    # Parse XML
    xml_data, gaps = parse_xml_with_gaps(xml_path)
except XMLParsingError as e:
    logger.error(f"XML parsing failed: {e}")
    # Fallback: Try PDF-only parsing
    return parse_pdf_only(pdf_path)

try:
    # Extract from PDF
    pdf_data = extract_pdf_gaps(pdf_path, gaps)
except PDFExtractionError as e:
    logger.warning(f"PDF extraction failed: {e}")
    # Continue with XML-only data
    pdf_data = {}

# Merge always succeeds (even with empty PDF data)
merged_data = merge_data(xml_data, pdf_data)

# Validation may fail
validation = validate(merged_data)
if validation.overall_status == 'fail':
    raise TranslationBlockedError(validation.critical_gaps)
```

---

## 8. Performance Considerations

### 8.1 Optimization Strategies

1. **Lazy PDF Loading**: Only load PDF if gaps detected
2. **Cached Extraction**: Cache PDF extraction results
3. **Parallel Processing**: Parse XML and PDF in parallel
4. **Selective Extraction**: Extract only needed PDF sections
5. **Incremental Validation**: Validate sections as they're parsed

### 8.2 Performance Targets

| Operation | Target Time | Max Time |
|-----------|-------------|----------|
| XML Parsing | < 2s | 5s |
| Gap Detection | < 0.5s | 1s |
| PDF Extraction | < 5s | 15s |
| Data Merging | < 0.5s | 1s |
| Validation | < 1s | 2s |
| Report Generation | < 1s | 2s |
| **Total Pipeline** | **< 10s** | **25s** |

---

## 9. Testing Strategy

### 9.1 Unit Tests

- Test each component independently
- Mock dependencies (PDF reader, XML parser)
- Test edge cases (empty fields, malformed data)

### 9.2 Integration Tests

- Test complete pipeline with real SDS files
- Test with various gap scenarios
- Test error handling and fallbacks

### 9.3 Test Cases

```python
# Test Case 1: Complete XML (no gaps)
def test_complete_xml_no_pdf_needed():
    result = parse_sds_hybrid(complete_xml_path)
    assert result.merge_summary['pdf'] == 0
    assert result.validation.overall_status == 'pass'

# Test Case 2: XML with gaps, PDF available
def test_xml_gaps_filled_from_pdf():
    result = parse_sds_hybrid(incomplete_xml_path, pdf_path)
    assert result.merge_summary['pdf'] > 0
    assert result.validation.overall_status == 'pass'

# Test Case 3: XML with gaps, no PDF
def test_xml_gaps_no_pdf():
    result = parse_sds_hybrid(incomplete_xml_path)
    assert result.validation.overall_status == 'warning'
    assert len(result.validation.warnings) > 0

# Test Case 4: Critical gaps block translation
def test_critical_gaps_block_translation():
    with pytest.raises(TranslationBlockedError):
        result = parse_sds_hybrid(critical_gaps_xml_path)
        gate = PreTranslationGate()
        gate.check(result.validation)
```

---

## 10. Deployment

### 10.1 Integration Steps

1. Install new dependencies: `pip install pdfplumber`
2. Add new modules to project
3. Update `sds_xml_importer.py` to use hybrid parser
4. Update Flask routes to handle validation
5. Add gap report template
6. Update documentation

### 10.2 Backward Compatibility

- Keep existing `parse_sds_xml()` function
- Add new `parse_sds_hybrid()` function
- Allow gradual migration
- Provide feature flag to enable/disable hybrid parsing

### 10.3 Configuration

```python
# config.py
HYBRID_PARSER_ENABLED = True
PDF_FALLBACK_ENABLED = True
VALIDATION_STRICT_MODE = False
GAP_REPORT_FORMAT = 'markdown'  # 'json', 'markdown', 'html'
```

---

## 11. Monitoring and Logging

### 11.1 Logging Strategy

```python
import logging

logger = logging.getLogger('sds_hybrid_parser')

# Log levels
logger.info("Starting hybrid parsing for {xml_path}")
logger.debug("Detected {len(gaps)} gaps in XML")
logger.warning("PDF extraction failed for section 8, using XML only")
logger.error("Critical gap detected: Section 16 completely missing")
```

### 11.2 Metrics to Track

- Number of gaps detected per SDS
- PDF extraction success rate
- Validation pass/fail rate
- Average processing time
- Data source distribution (XML vs PDF percentage)

---

## 12. Future Enhancements

### 12.1 Phase 2 Features

1. **Machine Learning Gap Prediction**: Predict missing values based on similar SDS
2. **Multi-PDF Support**: Extract from multiple PDF versions
3. **Real-time Validation UI**: Web interface for gap report
4. **Automatic XML Enhancement**: Generate improved XML from PDF data
5. **Batch Processing**: Process multiple SDS files in parallel

### 12.2 Extensibility Points

- Plugin system for custom gap detectors
- Custom PDF extraction rules per SDS provider
- Configurable validation rules
- Custom report templates

---

## 13. Security Considerations

### 13.1 Input Validation

- Validate XML structure before parsing
- Sanitize PDF content before extraction
- Limit file sizes (XML < 10MB, PDF < 50MB)
- Validate file types

### 13.2 Data Privacy

- No sensitive data logged
- Temporary files cleaned up after processing
- Optional data anonymization for reports

---

## 14. Documentation Requirements

### 14.1 User Documentation

- How to use hybrid parser
- Understanding gap reports
- Troubleshooting guide
- Configuration options

### 14.2 Developer Documentation

- API reference
- Architecture overview
- Adding new gap detection rules
- Extending PDF extraction

---

## 15. Success Metrics

The design is successful when:

- ✅ All identified gaps are filled from PDF
- ✅ Processing time < 10 seconds for typical SDS
- ✅ Validation accuracy > 95%
- ✅ PDF extraction success rate > 90%
- ✅ Zero hardcoded data in parsers
- ✅ Gap report generated for every SDS
- ✅ Translation blocked when critical gaps exist
- ✅ All tests pass (unit + integration)
