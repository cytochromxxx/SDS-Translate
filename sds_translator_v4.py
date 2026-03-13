#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS HTML Translator Tool v4 - Fixed Partial Word Replacement Issues

Key improvements:
- Word boundary detection to prevent Teilwort-Ersetzungen
- Proper handling of section number prefixes
- Exact match validation with substring contamination prevention
- Strict matching mode for critical phrases
"""

import sys
import sqlite3
import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from typing import Dict, List, Tuple, Optional
import html

sys.stdout.reconfigure(encoding='utf-8')


class SDSTranslator:
    """Translates SDS HTML files using a phrase database with strict matching."""
    
    AVAILABLE_LANGUAGES = {
        'de': 'de_original', 'fr': 'fr_original', 'es': 'es_original',
        'it': 'it_original', 'nl': 'nl_original', 'pl': 'pl_original',
        'sv': 'sv_original', 'da': 'da_original', 'fi': 'fi_original',
        'el': 'el_original', 'cs': 'cs_original', 'hu': 'hu_original',
        'ro': 'ro_original', 'bg': 'bg_original', 'sk': 'sk_original',
        'sl': 'sl_original', 'et': 'et_original', 'lv': 'lv_original',
        'lt': 'lt_original', 'hr': 'hr_original', 'pt': 'pt_original',
        'no': 'no_original', 'is': 'is_original', 'mt': 'mt_original'
    }
    
    SKIP_TAGS = {'script', 'style', 'meta', 'link', 'title', 'head'}
    
    # Minimum phrase length to prevent Teilwort-Ersetzungen
    MIN_PHRASE_LENGTH = 4
    
    def __init__(self, db_path: str, target_lang: str, debug: bool = True):
        self.db_path = db_path
        self.target_lang = target_lang.lower()
        self.debug = debug
        
        if self.target_lang not in self.AVAILABLE_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_lang}")
        
        self.target_column = self.AVAILABLE_LANGUAGES[self.target_lang]
        self.phrase_cache = {}  # normalized -> (original, translation)
        self.phrase_patterns = []  # List of (original, normalized, translation)
        self.stats = {
            'total_texts': 0, 'translated_exact': 0, 'not_found': 0,
            'skipped_empty': 0, 'skipped_tags': 0, 'partial_match_rejected': 0
        }
        self.not_found_log = []
        self.original_content = ""
        
    def _load_phrases(self):
        """Load all phrases from database with strict filtering."""
        print(f"Loading phrases from database: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = f"""
            SELECT en_original, {self.target_column}
            FROM phrases
            WHERE en_original IS NOT NULL 
              AND en_original != ''
              AND length(en_original) >= {self.MIN_PHRASE_LENGTH}
              AND {self.target_column} IS NOT NULL
              AND {self.target_column} != ''
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for en_text, translated_text in rows:
            if en_text and translated_text:
                normalized = self._normalize_text(en_text)
                # Skip very short normalized text
                if len(normalized) >= self.MIN_PHRASE_LENGTH:
                    self.phrase_cache[normalized] = (en_text, translated_text)
                    self.phrase_patterns.append((en_text, normalized, translated_text))
        
        # Sort by length (longest first) for proper matching priority
        self.phrase_patterns.sort(key=lambda x: len(x[0]), reverse=True)
        
        conn.close()
        print(f"Loaded {len(self.phrase_cache)} phrases into cache")
        
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        text = html.unescape(str(text))
        # Normalize whitespace but preserve structure
        text = ' '.join(text.split())
        return text.strip()
        
    def _has_word_boundaries(self, text: str, match_start: int, match_end: int) -> bool:
        """
        Check if the match has proper word boundaries.
        Prevents Teilwort-Ersetzungen like 'identifier' matching inside 'identifiers'.
        """
        # Check left boundary
        if match_start > 0:
            char_before = text[match_start - 1]
            if char_before.isalnum() or char_before in "'_-":
                return False
                
        # Check right boundary
        if match_end < len(text):
            char_after = text[match_end]
            if char_after.isalnum() or char_after in "'_-":
                return False
                
        return True
        
    def _strip_section_number(self, text: str) -> Tuple[str, str]:
        """Strip section numbers from the beginning of text."""
        pattern = r'^(\d{1,2}(?:\.\d{1,2})*\.?\s*)'
        match = re.match(pattern, text)
        
        if match:
            section_number = match.group(1)
            remaining = text[len(section_number):].strip()
            return section_number, remaining
        
        return "", text
        
    def _find_exact_translation(self, text: str) -> Tuple[Optional[str], str, str]:
        """
        Find exact translation with strict boundary validation.
        Ignores trailing punctuation for matching.
        """
        normalized = self._normalize_text(text)
        
        if not normalized:
            return None, 'none', ""
            
        # Direct lookup with full text
        if normalized in self.phrase_cache:
            return self.phrase_cache[normalized][1], 'exact', normalized
        
        # Try case-insensitive lookup
        normalized_lower = normalized.lower()
        for key, (original, translation) in self.phrase_cache.items():
            if key.lower() == normalized_lower:
                return translation, 'case_insensitive', key
        
        # Try adding common punctuation marks to find match in database
        # This handles cases where database has "Phrase." but input is "Phrase"
        for punct in ['.', '!', '?', ':', ';']:
            with_punct = normalized + punct
            if with_punct in self.phrase_cache:
                return self.phrase_cache[with_punct][1], 'added_punct', with_punct
        
        # Try stripping trailing punctuation
        stripped = normalized.rstrip(':;.!?')
        if stripped != normalized:
            # First try the stripped version directly
            if stripped in self.phrase_cache:
                return self.phrase_cache[stripped][1], 'stripped', stripped
            
            # Then try adding punctuation to stripped version
            for punct in ['.', '!', '?', ':', ';']:
                with_punct = stripped + punct
                if with_punct in self.phrase_cache:
                    return self.phrase_cache[with_punct][1], 'stripped_punct', with_punct
        
        # Try stripping section numbers
        section_number, remaining = self._strip_section_number(normalized)
        if section_number and remaining:
            if remaining in self.phrase_cache:
                translation = self.phrase_cache[remaining][1]
                # Reconstruct: section number + space + translation
                return section_number.rstrip() + ' ' + translation, 'section_number', remaining
            
            # Case-insensitive with section number
            remaining_lower = remaining.lower()
            for key, (original, translation) in self.phrase_cache.items():
                if key.lower() == remaining_lower:
                    return section_number.rstrip() + ' ' + translation, 'section_number_ci', remaining
            
            # Try with punctuation for section number case
            for punct in ['.', '!', '?', ':', ';']:
                with_punct = remaining + punct
                if with_punct in self.phrase_cache:
                    translation = self.phrase_cache[with_punct][1]
                    return section_number.rstrip() + ' ' + translation, 'section_number_punct', with_punct
        
        return None, 'none', ""
        
    def _find_substring_matches(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Find substring matches with strict word boundary validation.
        Prevents Teilwort-Ersetzungen.
        """
        results = []
        normalized = self._normalize_text(text)
        
        if not normalized:
            return results
        
        # Track matched positions to avoid overlaps
        matched_ranges = []
        
        # Try each pattern (longest first)
        for original, pattern_normalized, translation in self.phrase_patterns:
            pattern_len = len(pattern_normalized)
            
            # Skip very short patterns
            if pattern_len < self.MIN_PHRASE_LENGTH:
                continue
            
            # Find all occurrences with word boundary checking
            start = 0
            while True:
                idx = normalized.find(pattern_normalized, start)
                if idx == -1:
                    break
                
                end = idx + pattern_len
                
                # Check for overlapping matches
                overlap = False
                for m_start, m_end in matched_ranges:
                    if not (end <= m_start or idx >= m_end):
                        overlap = True
                        break
                
                if not overlap:
                    # Strict word boundary check
                    if self._has_word_boundaries(normalized, idx, end):
                        # Map normalized positions back to original text
                        orig_start = self._map_to_original(text, normalized, idx)
                        orig_end = self._map_to_original(text, normalized, end)
                        
                        if orig_start is not None and orig_end is not None:
                            results.append((orig_start, orig_end, original, translation))
                            matched_ranges.append((idx, end))
                    else:
                        self.stats['partial_match_rejected'] += 1
                        if self.debug:
                            matched_text = normalized[idx:end]
                            print(f"  [Rejected partial match] '{matched_text}' in '{normalized[:50]}...'")
                
                start = idx + 1
        
        return results
        
    def _map_to_original(self, original: str, normalized: str, norm_pos: int) -> Optional[int]:
        """Map normalized position back to original text position."""
        orig_idx = 0
        norm_idx = 0
        
        while norm_idx < norm_pos and orig_idx < len(original):
            # Skip whitespace in original
            while orig_idx < len(original) and original[orig_idx] in ' \t\n\r':
                orig_idx += 1
            
            # Skip whitespace in normalized
            while norm_idx < len(normalized) and normalized[norm_idx] in ' \t\n\r':
                norm_idx += 1
            
            if norm_idx >= norm_pos:
                break
                
            if orig_idx < len(original) and norm_idx < len(normalized):
                if original[orig_idx] == normalized[norm_idx]:
                    orig_idx += 1
                    norm_idx += 1
                else:
                    orig_idx += 1
            else:
                orig_idx += 1
                
        return orig_idx
        
    def translate_html(self, html_content: str) -> str:
        """Translate HTML content with strict matching."""
        self._load_phrases()
        self.original_content = html_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        text_nodes = []
        for element in soup.find_all(string=True):
            if self._should_translate_element(element):
                text = str(element)
                if text.strip():
                    text_nodes.append((element, text))
        
        for element, text in text_nodes:
            self._process_text_node(element, text)
        
        return str(soup)
        
    def _should_translate_element(self, element) -> bool:
        """Check if an element should be translated."""
        if not isinstance(element, NavigableString):
            return False
        
        parent = element.parent
        while parent:
            if hasattr(parent, 'name') and parent.name in self.SKIP_TAGS:
                return False
            parent = parent.parent
        
        return True
        
    def _process_text_node(self, element: NavigableString, text: str):
        """Process a single text node with strict validation."""
        if not text:
            return

        self.stats['total_texts'] += 1
        
        stripped = text.strip()
        if not stripped:
            self.stats['skipped_empty'] += 1
            return
        
        # Try exact match first
        translation, match_type, matched_key = self._find_exact_translation(text)
        
        if translation:
            self.stats['translated_exact'] += 1
            leading_ws = text[:len(text) - len(text.lstrip())]
            trailing_ws = text[len(text.rstrip()):]
            final_text = leading_ws + translation + trailing_ws
            element.replace_with(final_text)
            return
        
        # Try substring matching for longer texts
        if len(stripped) > self.MIN_PHRASE_LENGTH:
            substring_matches = self._find_substring_matches(text)
            if substring_matches:
                final_text = self._apply_substring_translations(text, substring_matches)
                element.replace_with(final_text)
                self.stats['translated_exact'] += 1
                return
        
        # Not found
        self.stats['not_found'] += 1
        self.not_found_log.append({'text': stripped[:100], 'line': -1})
        
        if self.debug and self.stats['not_found'] <= 50:
            try:
                safe_text = stripped.encode('utf-8', errors='ignore').decode('utf-8')
                if len(safe_text) > 80:
                    safe_text = safe_text[:80] + "..."
                print(f"  [Not found] '{safe_text}'")
            except:
                pass
                
    def _apply_substring_translations(self, text: str, matches: List[Tuple[int, int, str, str]]) -> str:
        """Apply substring translations from end to start."""
        if not matches:
            return text
        
        result = text
        for start, end, original, translation in sorted(matches, key=lambda x: x[0], reverse=True):
            if start >= 0 and end <= len(result):
                actual_text = result[start:end]
                # Verify before replacing
                if self._normalize_text(actual_text) == self._normalize_text(original):
                    result = result[:start] + translation + result[end:]
        
        return result
        
    def print_stats(self):
        """Print translation statistics."""
        print("\n" + "="*60)
        print("Translation Statistics:")
        print(f"  Total text segments:     {self.stats['total_texts']}")
        print(f"  Translated:              {self.stats['translated_exact']}")
        print(f"  Not found:               {self.stats['not_found']}")
        print(f"  Skipped (empty):         {self.stats['skipped_empty']}")
        print(f"  Partial matches rejected:{self.stats['partial_match_rejected']}")
        
        if self.stats['total_texts'] > 0:
            coverage = (self.stats['translated_exact'] / self.stats['total_texts']) * 100
            print(f"  Coverage:                {coverage:.1f}%")
        
        print("="*60)


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python sds_translator_v4.py <input.html> <target_language> [output.html]")
        print("Example: python sds_translator_v4.py input.html de output.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_lang = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    db_path = "sds_dictionary_final.db"
    
    translator = SDSTranslator(db_path, target_lang, debug=True)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    translated = translator.translate_html(html_content)
    
    translator.print_stats()
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated)
        print(f"\nTranslated HTML written to: {output_file}")
    else:
        print(translated)


if __name__ == "__main__":
    main()
