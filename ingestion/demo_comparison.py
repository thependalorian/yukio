"""
Comparison demo: Regex-based vs spaCy-based Japanese text processing.
Shows the concrete improvements you get with spaCy integration.
"""

import re
from japanese_processor import get_japanese_processor


def regex_split_sentences(text: str) -> list:
    """Original regex-based sentence splitting."""
    sentences = re.split(r'([。！？])', text)
    result = []
    current = ""

    for part in sentences:
        current += part
        if part in '。！？':
            if current.strip():
                result.append(current.strip())
            current = ""

    if current.strip():
        result.append(current.strip())

    return result


def spacy_split_sentences(text: str) -> list:
    """spaCy-based sentence splitting."""
    processor = get_japanese_processor(use_spacy=True)
    return processor.split_sentences(text)


def demo_sentence_splitting():
    """Compare sentence splitting methods."""
    print("\n" + "="*70)
    print("DEMO 1: Sentence Splitting Comparison")
    print("="*70)

    # Test case 1: Simple sentences
    test1 = "私は学生です。東京に住んでいます。毎日勉強します。"

    print("\n📝 Test 1: Simple sentences")
    print(f"Input: {test1}\n")

    print("Regex-based:")
    regex_result = regex_split_sentences(test1)
    for i, sent in enumerate(regex_result, 1):
        print(f"  {i}. {sent}")

    print("\nspaCy-based:")
    spacy_result = spacy_split_sentences(test1)
    for i, sent in enumerate(spacy_result, 1):
        print(f"  {i}. {sent}")

    # Test case 2: Complex sentences with embedded clauses
    test2 = "私が昨日買った本は、とても面白いです。友達に勧めたいと思います。"

    print("\n📝 Test 2: Complex sentences with embedded clauses")
    print(f"Input: {test2}\n")

    print("Regex-based:")
    regex_result = regex_split_sentences(test2)
    for i, sent in enumerate(regex_result, 1):
        print(f"  {i}. {sent}")

    print("\nspaCy-based:")
    spacy_result = spacy_split_sentences(test2)
    for i, sent in enumerate(spacy_result, 1):
        print(f"  {i}. {sent}")


def demo_tokenization():
    """Compare tokenization methods."""
    print("\n" + "="*70)
    print("DEMO 2: Tokenization Comparison")
    print("="*70)

    text = "私は日本語を勉強しています。"

    print(f"\n📝 Input: {text}\n")

    # Simple split (what regex would do)
    print("Simple character split:")
    chars = list(text)
    print(f"  {chars}")
    print(f"  Count: {len(chars)} characters")

    # spaCy tokenization
    processor = get_japanese_processor(use_spacy=True)
    tokens = processor.tokenize(text)

    print("\nspaCy tokenization (linguistic units):")
    print(f"  {tokens}")
    print(f"  Count: {len(tokens)} tokens")

    print("\n💡 Notice: spaCy breaks 勉強しています into meaningful units:")
    print("  勉強 (study) + し (verb stem) + て (te-form) + い (auxiliary) + ます (polite)")


def demo_linguistic_analysis():
    """Show linguistic features from spaCy."""
    print("\n" + "="*70)
    print("DEMO 3: Linguistic Analysis (spaCy-only feature)")
    print("="*70)

    text = """
    私は東京大学の学生です。
    毎日、図書館で日本語を勉強しています。
    来年、JLPTのN2試験を受ける予定です。
    """

    processor = get_japanese_processor(use_spacy=True)
    features = processor.extract_linguistic_features(text)

    print(f"\n📝 Input:")
    print(text)

    print("\n📊 Analysis Results:")
    print(f"  Sentences: {features['sentence_count']}")
    print(f"  Tokens: {features['token_count']}")

    print(f"\n  Character Distribution:")
    for char_type, count in features['character_counts'].items():
        print(f"    {char_type}: {count}")

    if 'pos_counts' in features:
        print(f"\n  Part-of-Speech Distribution:")
        for pos, count in sorted(features['pos_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {pos}: {count}")

    if 'entities' in features:
        print(f"\n  Named Entities Found:")
        for entity in features['entities']:
            print(f"    • {entity['text']} ({entity['label']})")


def demo_chunking():
    """Compare chunking strategies."""
    print("\n" + "="*70)
    print("DEMO 4: Smart Chunking Boundaries")
    print("="*70)

    text = """
    日本語の助詞は難しいです。「は」と「が」の違いを理解するのは大変です。
    しかし、たくさん練習すれば、だんだん分かるようになります。
    毎日少しずつ勉強することが大切です。諦めずに頑張りましょう。
    """

    processor = get_japanese_processor(use_spacy=True)

    print(f"\n📝 Input text ({len(text)} chars):")
    print(text)

    # Get smart boundaries
    boundaries = processor.smart_chunk_boundaries(text, target_size=60, max_size=100)

    print(f"\n📊 spaCy Smart Chunking (target: 60 chars, max: 100 chars):")
    print(f"Created {len(boundaries)} chunks at natural sentence boundaries:\n")

    for i, (start, end) in enumerate(boundaries, 1):
        chunk = text[start:end].strip()
        print(f"Chunk {i} ({len(chunk)} chars):")
        print(f"  {chunk}\n")

    print("💡 Notice: Each chunk ends at a sentence boundary (。)")
    print("   This preserves semantic coherence for better embeddings!")


def demo_benefits_for_rag():
    """Show benefits for RAG/LanceDB."""
    print("\n" + "="*70)
    print("DEMO 5: Benefits for RAG & Vector Search")
    print("="*70)

    print("\n🎯 With spaCy integration, your LanceDB chunks will have:")

    print("\n1. **Better Context Preservation**")
    print("   ❌ Regex: 'これは本です。私は学' (cuts mid-sentence)")
    print("   ✅ spaCy: 'これは本です。' (complete sentence)")

    print("\n2. **Smarter Metadata for Filtering**")
    print("   • Named entities: Filter by location, person names")
    print("   • POS distribution: Find example sentences vs explanations")
    print("   • Complexity metrics: Match to user's JLPT level")

    print("\n3. **Improved Embeddings**")
    print("   • Sentence-level chunks = better semantic similarity")
    print("   • No broken context = more accurate retrieval")

    print("\n4. **Rich Metadata Example**")
    print("   {")
    print('     "content": "東京は日本の首都です。",')
    print('     "has_japanese": true,')
    print('     "jlpt_level": "N5",')
    print('     "content_type": "grammar",')
    print('     "pos_distribution": {"NOUN": 3, "VERB": 1, "PARTICLE": 2},')
    print('     "entities": [{"text": "東京", "label": "GPE"}, {"text": "日本", "label": "GPE"}],')
    print('     "sentence_count": 1,')
    print('     "token_count": 11')
    print("   }")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("🏯 YUKIO - Japanese Processing: Regex vs spaCy Comparison")
    print("="*70)

    demo_sentence_splitting()
    demo_tokenization()
    demo_linguistic_analysis()
    demo_chunking()
    demo_benefits_for_rag()

    print("\n" + "="*70)
    print("✅ Demo Complete!")
    print("="*70)
    print("\nTo integrate spaCy into your pipeline, see INTEGRATION_GUIDE.md")
    print()


if __name__ == "__main__":
    main()
