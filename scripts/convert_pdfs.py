#!/usr/bin/env python3
"""
Convert Japanese learning documents (PDF, EPUB) to Markdown.

This script converts all PDF and EPUB files in the data/japanese directory
to markdown format for ingestion into the RAG system.

- PDFs: Docling (excellent table extraction, OCR, layout analysis)
- EPUBs: EbookLib (native EPUB support with metadata extraction)

Dependencies:
    pip install docling ebooklib beautifulsoup4 tqdm
"""

import re
from pathlib import Path
from typing import Tuple
from tqdm import tqdm

# PDF conversion - Docling
from docling.document_converter import DocumentConverter

# EPUB conversion - EbookLib
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def clean_html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content to clean markdown.

    Args:
        html_content: Raw HTML string from EPUB

    Returns:
        Cleaned markdown text
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()

    # Convert common HTML elements to markdown
    markdown_lines = []

    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote']):
        text = element.get_text(strip=True)
        if not text:
            continue

        if element.name == 'h1':
            markdown_lines.append(f"\n# {text}\n")
        elif element.name == 'h2':
            markdown_lines.append(f"\n## {text}\n")
        elif element.name == 'h3':
            markdown_lines.append(f"\n### {text}\n")
        elif element.name == 'h4':
            markdown_lines.append(f"\n#### {text}\n")
        elif element.name == 'h5':
            markdown_lines.append(f"\n##### {text}\n")
        elif element.name == 'h6':
            markdown_lines.append(f"\n###### {text}\n")
        elif element.name == 'li':
            markdown_lines.append(f"- {text}")
        elif element.name == 'blockquote':
            markdown_lines.append(f"> {text}\n")
        elif element.name == 'p':
            markdown_lines.append(f"\n{text}\n")

    # If no structured elements found, fall back to plain text
    if not markdown_lines:
        text = soup.get_text(separator='\n', strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    result = '\n'.join(markdown_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


def extract_epub_metadata(book: epub.EpubBook) -> dict:
    """
    Extract metadata from EPUB book.

    Args:
        book: EpubBook object

    Returns:
        Dictionary of metadata
    """
    metadata = {}

    title = book.get_metadata('DC', 'title')
    metadata['title'] = title[0][0] if title else 'Unknown Title'

    creator = book.get_metadata('DC', 'creator')
    metadata['author'] = creator[0][0] if creator else 'Unknown Author'

    language = book.get_metadata('DC', 'language')
    metadata['language'] = language[0][0] if language else 'ja'

    publisher = book.get_metadata('DC', 'publisher')
    metadata['publisher'] = publisher[0][0] if publisher else None

    return metadata


def convert_epub_to_markdown(epub_path: Path) -> Tuple[str, dict]:
    """
    Convert EPUB file to markdown.

    Args:
        epub_path: Path to EPUB file

    Returns:
        Tuple of (markdown_content, metadata)
    """
    book = epub.read_epub(str(epub_path), options={'ignore_ncx': True})
    metadata = extract_epub_metadata(book)

    markdown_parts = []

    # Add book title as main header
    markdown_parts.append(f"# {metadata['title']}\n")
    if metadata.get('author') and metadata['author'] != 'Unknown Author':
        markdown_parts.append(f"**Author:** {metadata['author']}\n")

    markdown_parts.append("\n---\n")

    # Extract content from each chapter/item
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                content = item.get_content().decode('utf-8', errors='ignore')
                markdown_content = clean_html_to_markdown(content)

                if markdown_content.strip():
                    markdown_parts.append(markdown_content)
            except Exception as e:
                print(f"    Warning: Could not process item {item.get_name()}: {e}")
                continue

    full_markdown = '\n\n'.join(markdown_parts)
    full_markdown = re.sub(r'\n{4,}', '\n\n\n', full_markdown)

    return full_markdown, metadata


def create_safe_filename(name: str, max_length: int = 80) -> str:
    """
    Create a safe filename from a string.

    Args:
        name: Original filename or title
        max_length: Maximum length of filename

    Returns:
        Safe filename string
    """
    safe_name = name[:max_length]
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in safe_name)
    safe_name = re.sub(r'_+', '_', safe_name)
    return safe_name.strip('_')


def convert_documents_to_markdown(
    input_dir: str = "data/japanese",
    output_dir: str = "data/japanese/markdown"
):
    """
    Convert all PDFs and EPUBs in input directory to markdown.

    Args:
        input_dir: Directory containing source files
        output_dir: Directory to save markdown files
    """
    # Get script directory and project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    input_path = project_root / input_dir
    output_path = project_root / output_dir

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDF and EPUB files
    pdf_files = list(input_path.glob("*.pdf"))
    epub_files = list(input_path.glob("*.epub"))

    all_files = pdf_files + epub_files

    if not all_files:
        print(f"No PDF or EPUB files found in {input_path}")
        return

    print(f"Found {len(pdf_files)} PDF files and {len(epub_files)} EPUB files")
    print(f"Output directory: {output_path}")
    print("-" * 50)

    # Initialize PDF converter (Docling)
    pdf_converter = None  # Lazy init

    # Track results
    successful = []
    failed = []

    # Convert each file
    for source_file in tqdm(all_files, desc="Converting documents"):
        try:
            # Create safe filename
            safe_name = create_safe_filename(source_file.stem)
            output_file = output_path / f"{safe_name}.md"

            # Skip if already converted
            if output_file.exists():
                print(f"  Skipping (exists): {safe_name}")
                successful.append(source_file.name)
                continue

            file_ext = source_file.suffix.lower()
            print(f"  Converting [{file_ext}]: {source_file.name[:50]}...")

            if file_ext == '.pdf':
                # Lazy initialize Docling converter
                if pdf_converter is None:
                    pdf_converter = DocumentConverter()

                # Convert PDF using Docling
                result = pdf_converter.convert(str(source_file))
                markdown_content = result.document.export_to_markdown()

                # Add metadata header for PDF
                header = f"""---
title: "{source_file.stem}"
source: "{source_file.name}"
format: pdf
parser: docling
type: japanese_learning_material
---

"""
                final_content = header + markdown_content

            elif file_ext == '.epub':
                # Convert EPUB using EbookLib
                markdown_content, metadata = convert_epub_to_markdown(source_file)

                # Add metadata header for EPUB
                header = f"""---
title: "{metadata.get('title', source_file.stem)}"
author: "{metadata.get('author', 'Unknown')}"
language: "{metadata.get('language', 'ja')}"
source: "{source_file.name}"
format: epub
parser: ebooklib
type: japanese_learning_material
---

"""
                final_content = header + markdown_content

            else:
                print(f"  Skipping unsupported format: {file_ext}")
                continue

            # Write markdown file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_content)

            successful.append(source_file.name)
            print(f"  Saved: {output_file.name}")

        except Exception as e:
            failed.append((source_file.name, str(e)))
            print(f"  ERROR: {source_file.name[:40]} - {e}")

    # Print summary
    print("\n" + "=" * 50)
    print("CONVERSION SUMMARY")
    print("=" * 50)
    print(f"Total files: {len(all_files)}")
    print(f"  - PDFs: {len(pdf_files)}")
    print(f"  - EPUBs: {len(epub_files)}")
    print(f"Successful: {len(successful)}/{len(all_files)}")
    print(f"Failed: {len(failed)}/{len(all_files)}")

    if failed:
        print("\nFailed files:")
        for name, error in failed:
            print(f"  - {name[:50]}: {error[:80]}")

    print(f"\nMarkdown files saved to: {output_path}")


if __name__ == "__main__":
    convert_documents_to_markdown()
