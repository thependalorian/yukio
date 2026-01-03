"""
Japanese text processing using spaCy for advanced linguistic analysis.
Enhances chunking, tokenization, and metadata extraction for Japanese content.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
    logger.info("spaCy available for Japanese processing")
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available, using regex fallback for Japanese processing")


class JapaneseTextProcessor:
    """
    Advanced Japanese text processor using spaCy.
    Falls back to regex-based processing if spaCy is not available.
    """

    def __init__(self, use_spacy: bool = True):
        """
        Initialize Japanese text processor.

        Args:
            use_spacy: Whether to use spaCy (if available)
        """
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.nlp = None

        if self.use_spacy:
            try:
                self.nlp = self._load_spacy_model()
                logger.info("✅ Loaded spaCy Japanese model: ja_core_news_lg")
            except Exception as e:
                logger.warning(f"Failed to load spaCy model: {e}. Using regex fallback.")
                self.use_spacy = False

    @lru_cache(maxsize=1)
    def _load_spacy_model(self):
        """Load spaCy Japanese model (cached)."""
        return spacy.load('ja_core_news_lg')

    def split_sentences(self, text: str) -> List[str]:
        """
        Split Japanese text into sentences.

        Args:
            text: Japanese text to split

        Returns:
            List of sentences
        """
        if self.use_spacy and self.nlp:
            return self._spacy_split_sentences(text)
        else:
            return self._regex_split_sentences(text)

    def _spacy_split_sentences(self, text: str) -> List[str]:
        """
        Split sentences using spaCy's sentence segmentation.
        Much more accurate than regex for complex Japanese text.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        return sentences

    def _regex_split_sentences(self, text: str) -> List[str]:
        """
        Fallback regex-based sentence splitting.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on Japanese sentence enders: 。！？
        sentences = re.split(r'([。！？])', text)

        # Rejoin sentence with its punctuation
        result = []
        current = ""

        for part in sentences:
            current += part
            if part in '。！？':
                if current.strip():
                    result.append(current.strip())
                current = ""

        # Add remaining text
        if current.strip():
            result.append(current.strip())

        return result

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize Japanese text.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        if self.use_spacy and self.nlp:
            return self._spacy_tokenize(text)
        else:
            return self._simple_tokenize(text)

    def _spacy_tokenize(self, text: str) -> List[str]:
        """
        Tokenize using spaCy.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        doc = self.nlp(text)
        return [token.text for token in doc]

    def _simple_tokenize(self, text: str) -> List[str]:
        """
        Simple whitespace-based tokenization fallback.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        return text.split()

    def extract_linguistic_features(self, text: str) -> Dict[str, Any]:
        """
        Extract linguistic features from Japanese text.

        Args:
            text: Japanese text

        Returns:
            Dictionary of linguistic features
        """
        if self.use_spacy and self.nlp:
            return self._spacy_extract_features(text)
        else:
            return self._regex_extract_features(text)

    def _spacy_extract_features(self, text: str) -> Dict[str, Any]:
        """
        Extract features using spaCy's linguistic analysis.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of features
        """
        doc = self.nlp(text)

        # Count POS tags
        pos_counts = {}
        for token in doc:
            pos = token.pos_
            pos_counts[pos] = pos_counts.get(pos, 0) + 1

        # Extract named entities
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })

        # Count character types
        char_counts = self._count_character_types(text)

        return {
            "sentence_count": len(list(doc.sents)),
            "token_count": len(doc),
            "character_counts": char_counts,
            "pos_counts": pos_counts,
            "entities": entities,
            "has_japanese": char_counts["total_japanese"] > 0,
            "language": "japanese" if char_counts["total_japanese"] > 0 else "mixed"
        }

    def _regex_extract_features(self, text: str) -> Dict[str, Any]:
        """
        Extract features using regex (fallback).

        Args:
            text: Text to analyze

        Returns:
            Dictionary of features
        """
        char_counts = self._count_character_types(text)
        sentences = self._regex_split_sentences(text)

        return {
            "sentence_count": len(sentences),
            "token_count": len(self._simple_tokenize(text)),
            "character_counts": char_counts,
            "has_japanese": char_counts["total_japanese"] > 0,
            "language": "japanese" if char_counts["total_japanese"] > 0 else "mixed"
        }

    def _count_character_types(self, text: str) -> Dict[str, int]:
        """
        Count different Japanese character types.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with character counts
        """
        hiragana = len(re.findall(r'[\u3040-\u309F]', text))
        katakana = len(re.findall(r'[\u30A0-\u30FF]', text))
        kanji = len(re.findall(r'[\u4E00-\u9FFF]', text))

        return {
            "hiragana": hiragana,
            "katakana": katakana,
            "kanji": kanji,
            "total_japanese": hiragana + katakana + kanji
        }

    def smart_chunk_boundaries(
        self,
        text: str,
        target_size: int = 800,
        max_size: int = 1500
    ) -> List[Tuple[int, int]]:
        """
        Find smart chunk boundaries based on linguistic analysis.

        Args:
            text: Text to chunk
            target_size: Target chunk size in characters
            max_size: Maximum chunk size in characters

        Returns:
            List of (start, end) tuples for chunk boundaries
        """
        if self.use_spacy and self.nlp:
            return self._spacy_smart_boundaries(text, target_size, max_size)
        else:
            return self._regex_smart_boundaries(text, target_size, max_size)

    def _spacy_smart_boundaries(
        self,
        text: str,
        target_size: int,
        max_size: int
    ) -> List[Tuple[int, int]]:
        """
        Find chunk boundaries using spaCy sentence segmentation.

        Args:
            text: Text to chunk
            target_size: Target chunk size
            max_size: Maximum chunk size

        Returns:
            List of (start, end) boundaries
        """
        doc = self.nlp(text)
        sentences = list(doc.sents)

        boundaries = []
        current_start = 0
        current_end = 0
        current_size = 0

        for sent in sentences:
            sent_start = sent.start_char
            sent_end = sent.end_char
            sent_size = sent_end - sent_start

            # Check if adding this sentence exceeds target
            if current_size + sent_size > target_size and current_size > 0:
                # Save current chunk
                boundaries.append((current_start, current_end))
                current_start = sent_start
                current_end = sent_end
                current_size = sent_size
            else:
                # Add sentence to current chunk
                if current_size == 0:
                    current_start = sent_start
                current_end = sent_end
                current_size += sent_size

            # Force split if we exceed max size
            if current_size > max_size:
                boundaries.append((current_start, current_end))
                current_start = current_end
                current_size = 0

        # Add final chunk
        if current_size > 0:
            boundaries.append((current_start, current_end))

        return boundaries

    def _regex_smart_boundaries(
        self,
        text: str,
        target_size: int,
        max_size: int
    ) -> List[Tuple[int, int]]:
        """
        Find chunk boundaries using regex sentence splitting (fallback).

        Args:
            text: Text to chunk
            target_size: Target chunk size
            max_size: Maximum chunk size

        Returns:
            List of (start, end) boundaries
        """
        sentences = self._regex_split_sentences(text)

        boundaries = []
        current_start = 0
        current_text = ""

        for sent in sentences:
            # Find position of sentence in original text
            sent_pos = text.find(sent, current_start)
            if sent_pos == -1:
                continue

            potential_chunk = current_text + sent

            if len(potential_chunk) > target_size and current_text:
                # Save current chunk
                boundaries.append((current_start, current_start + len(current_text)))
                current_start = sent_pos
                current_text = sent
            else:
                if not current_text:
                    current_start = sent_pos
                current_text = potential_chunk

            # Force split if exceeding max size
            if len(current_text) > max_size:
                boundaries.append((current_start, current_start + len(current_text)))
                current_start = sent_pos + len(sent)
                current_text = ""

        # Add final chunk
        if current_text:
            boundaries.append((current_start, current_start + len(current_text)))

        return boundaries

    def is_japanese(self, text: str) -> bool:
        """
        Check if text contains Japanese characters.

        Args:
            text: Text to check

        Returns:
            True if text contains Japanese
        """
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
        return bool(re.search(japanese_pattern, text))


# Singleton instance
_japanese_processor = None


def get_japanese_processor(use_spacy: bool = True) -> JapaneseTextProcessor:
    """
    Get or create Japanese text processor singleton.

    Args:
        use_spacy: Whether to use spaCy

    Returns:
        JapaneseTextProcessor instance
    """
    global _japanese_processor

    if _japanese_processor is None:
        _japanese_processor = JapaneseTextProcessor(use_spacy=use_spacy)

    return _japanese_processor


# Example usage
if __name__ == "__main__":
    # Test the processor
    processor = get_japanese_processor()

    test_text = """
    日本語を勉強しています。
    私は東京に住んでいます。
    毎日、日本語の本を読みます。
    """

    print("=== Japanese Text Processing Demo ===\n")

    # Test sentence splitting
    sentences = processor.split_sentences(test_text)
    print(f"Sentences ({len(sentences)}):")
    for i, sent in enumerate(sentences, 1):
        print(f"  {i}. {sent}")

    print()

    # Test tokenization
    tokens = processor.tokenize(test_text)
    print(f"Tokens ({len(tokens)}):")
    print(f"  {', '.join(tokens[:10])}...")

    print()

    # Test feature extraction
    features = processor.extract_linguistic_features(test_text)
    print("Linguistic Features:")
    print(f"  Sentences: {features['sentence_count']}")
    print(f"  Tokens: {features['token_count']}")
    print(f"  Character counts: {features['character_counts']}")
    if 'pos_counts' in features:
        print(f"  POS tags: {features['pos_counts']}")
    if 'entities' in features:
        print(f"  Named entities: {features['entities']}")

    print()

    # Test chunking
    boundaries = processor.smart_chunk_boundaries(test_text, target_size=50, max_size=100)
    print(f"Smart chunk boundaries ({len(boundaries)}):")
    for i, (start, end) in enumerate(boundaries, 1):
        chunk = test_text[start:end]
        print(f"  {i}. [{start}:{end}] {chunk.strip()[:50]}...")
