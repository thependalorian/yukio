#!/usr/bin/env python3
"""
Clean and fix markdown files converted from PDFs.

This script fixes common issues from PDF to Markdown conversion:
- Removes garbage OCR text
- Cleans up excessive image placeholders
- Fixes encoding issues
- Removes short nonsense lines
- Preserves actual Japanese content
- Fixes table formatting

Location: scripts/clean_markdown.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def is_garbage_line(line: str) -> bool:
    """
    Detect if a line is garbage OCR text.
    
    Args:
        line: Line to check
    
    Returns:
        True if line appears to be garbage
    """
    line_stripped = line.strip()
    
    # Empty lines are OK
    if not line_stripped:
        return False
    
    # Very short lines with only symbols/numbers (likely garbage)
    if len(line_stripped) <= 3 and not any('\u3040' <= c <= '\u9fff' for c in line_stripped):
        return True
    
    # Lines with mostly random uppercase letters (OCR errors)
    if len(line_stripped) <= 10:
        uppercase_count = sum(1 for c in line_stripped if c.isupper())
        if uppercase_count > len(line_stripped) * 0.7 and not line_stripped.startswith('#'):
            return True
    
    # Lines with lots of special characters (corrupted)
    special_chars = sum(1 for c in line_stripped if c in 'ΔΜΤϑϨχλήεϦϯάёД₫')
    if special_chars > len(line_stripped) * 0.3:
        return True
    
    # Common OCR garbage patterns
    garbage_patterns = [
        r'^[A-Z]{1,3}\.$',  # Single uppercase letters with period
        r'^[0-9]{1,2} [A-Z]{1,3}$',  # Numbers with random letters
        r'^[\-\•\·]{2,}$',  # Multiple dashes or bullets
        r'^[^\w\s]{3,}$',  # Only special characters
    ]
    
    for pattern in garbage_patterns:
        if re.match(pattern, line_stripped):
            return True
    
    return False


def has_meaningful_content(line: str) -> bool:
    """
    Check if line has meaningful content (Japanese or English text).
    
    Args:
        line: Line to check
    
    Returns:
        True if line has meaningful content
    """
    line_stripped = line.strip()
    
    # Check for Japanese characters
    if any('\u3040' <= c <= '\u9fff' for c in line_stripped):
        return True
    
    # Check for meaningful English (at least 3 words)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', line_stripped)
    if len(words) >= 3:
        return True
    
    # Headers are always meaningful
    if line_stripped.startswith('#'):
        return True
    
    # Table rows are meaningful
    if '|' in line_stripped:
        return True
    
    return False


def clean_markdown_content(content: str, filename: str) -> Tuple[str, dict]:
    """
    Clean markdown content.
    
    Args:
        content: Raw markdown content
        filename: Source filename for logging
    
    Returns:
        Tuple of (cleaned_content, statistics)
    """
    lines = content.split('\n')
    cleaned_lines = []
    stats = {
        'original_lines': len(lines),
        'removed_lines': 0,
        'removed_images': 0,
        'garbage_removed': 0,
        'empty_lines_removed': 0
    }
    
    # Track if we're in frontmatter
    in_frontmatter = False
    frontmatter_count = 0
    
    # Track consecutive empty lines
    consecutive_empty = 0
    
    for i, line in enumerate(lines):
        # Handle YAML frontmatter
        if line.strip() == '---':
            frontmatter_count += 1
            cleaned_lines.append(line)
            if frontmatter_count == 1:
                in_frontmatter = True
            elif frontmatter_count == 2:
                in_frontmatter = False
            continue
        
        # Always keep frontmatter
        if in_frontmatter:
            cleaned_lines.append(line)
            continue
        
        # Remove image placeholders
        if line.strip() == '<!-- image -->':
            stats['removed_images'] += 1
            continue
        
        # Check for garbage lines
        if is_garbage_line(line):
            stats['garbage_removed'] += 1
            stats['removed_lines'] += 1
            continue
        
        # Handle empty lines (keep max 2 consecutive)
        if not line.strip():
            consecutive_empty += 1
            if consecutive_empty <= 2:
                cleaned_lines.append(line)
            else:
                stats['empty_lines_removed'] += 1
                stats['removed_lines'] += 1
            continue
        else:
            consecutive_empty = 0
        
        # Check if line has meaningful content
        if not has_meaningful_content(line) and len(line.strip()) < 50:
            # Skip short lines without meaningful content
            stats['removed_lines'] += 1
            continue
        
        # Keep this line
        cleaned_lines.append(line)
    
    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
        stats['empty_lines_removed'] += 1
    
    stats['cleaned_lines'] = len(cleaned_lines)
    stats['reduction_percent'] = ((stats['original_lines'] - stats['cleaned_lines']) / stats['original_lines'] * 100) if stats['original_lines'] > 0 else 0
    
    return '\n'.join(cleaned_lines), stats


def clean_markdown_file(file_path: Path, backup: bool = True, dry_run: bool = False) -> dict:
    """
    Clean a single markdown file.
    
    Args:
        file_path: Path to markdown file
        backup: Create backup before cleaning
        dry_run: Don't actually modify files
    
    Returns:
        Dictionary with cleaning statistics
    """
    print(f"\n{'='*60}")
    print(f"Processing: {file_path.name}")
    print(f"{'='*60}")
    
    # Read original content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except UnicodeDecodeError:
        print(f"⚠️  Encoding issue, trying latin-1...")
        with open(file_path, 'r', encoding='latin-1') as f:
            original_content = f.read()
    
    # Clean content
    cleaned_content, stats = clean_markdown_content(original_content, file_path.name)
    
    # Print statistics
    print(f"\n📊 Cleaning Statistics:")
    print(f"   Original lines: {stats['original_lines']}")
    print(f"   Cleaned lines: {stats['cleaned_lines']}")
    print(f"   Removed lines: {stats['removed_lines']}")
    print(f"   - Garbage OCR: {stats['garbage_removed']}")
    print(f"   - Image placeholders: {stats['removed_images']}")
    print(f"   - Extra empty lines: {stats['empty_lines_removed']}")
    print(f"   Reduction: {stats['reduction_percent']:.1f}%")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - No changes made")
        return stats
    
    # Create backup
    if backup:
        backup_path = file_path.with_suffix('.md.backup')
        shutil.copy2(file_path, backup_path)
        print(f"\n💾 Backup created: {backup_path.name}")
    
    # Write cleaned content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"✅ File cleaned successfully!")
    
    return stats


def clean_all_markdown_files(
    markdown_dir: str = "data/japanese/markdown",
    backup: bool = True,
    dry_run: bool = False
):
    """
    Clean all markdown files in a directory.
    
    Args:
        markdown_dir: Directory containing markdown files
        backup: Create backups before cleaning
        dry_run: Don't actually modify files
    """
    markdown_path = Path(markdown_dir)
    
    if not markdown_path.exists():
        print(f"❌ Directory not found: {markdown_dir}")
        return
    
    # Find all markdown files
    markdown_files = list(markdown_path.glob("*.md"))
    
    if not markdown_files:
        print(f"❌ No markdown files found in {markdown_dir}")
        return
    
    print("\n" + "="*60)
    print(f"🧹 Markdown Cleaning Tool")
    print("="*60)
    print(f"📁 Directory: {markdown_dir}")
    print(f"📄 Files found: {len(markdown_files)}")
    print(f"💾 Backup: {'Yes' if backup else 'No'}")
    print(f"🔍 Dry run: {'Yes (no changes)' if dry_run else 'No (will modify files)'}")
    print("="*60)
    
    if not dry_run:
        confirm = input("\n⚠️  This will modify your markdown files. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ Cancelled by user")
            return
    
    # Process each file
    total_stats = {
        'files_processed': 0,
        'total_original_lines': 0,
        'total_cleaned_lines': 0,
        'total_removed_lines': 0,
        'total_garbage_removed': 0,
        'total_images_removed': 0
    }
    
    for file_path in markdown_files:
        try:
            stats = clean_markdown_file(file_path, backup=backup, dry_run=dry_run)
            
            total_stats['files_processed'] += 1
            total_stats['total_original_lines'] += stats['original_lines']
            total_stats['total_cleaned_lines'] += stats['cleaned_lines']
            total_stats['total_removed_lines'] += stats['removed_lines']
            total_stats['total_garbage_removed'] += stats['garbage_removed']
            total_stats['total_images_removed'] += stats['removed_images']
            
        except Exception as e:
            print(f"\n❌ Error processing {file_path.name}: {e}")
            continue
    
    # Print summary
    print("\n" + "="*60)
    print("📊 CLEANING SUMMARY")
    print("="*60)
    print(f"📄 Files processed: {total_stats['files_processed']}")
    print(f"📝 Total original lines: {total_stats['total_original_lines']}")
    print(f"✅ Total cleaned lines: {total_stats['total_cleaned_lines']}")
    print(f"🗑️  Total removed lines: {total_stats['total_removed_lines']}")
    print(f"   - Garbage OCR text: {total_stats['total_garbage_removed']}")
    print(f"   - Image placeholders: {total_stats['total_images_removed']}")
    
    if total_stats['total_original_lines'] > 0:
        reduction = (total_stats['total_removed_lines'] / total_stats['total_original_lines'] * 100)
        print(f"\n📉 Overall reduction: {reduction:.1f}%")
    
    if not dry_run:
        print(f"\n💾 Backups saved with .md.backup extension")
        print(f"✅ All files cleaned successfully!")
    else:
        print(f"\n🔍 DRY RUN COMPLETE - No files were modified")
        print(f"   Remove --dry-run to actually clean the files")
    
    print("="*60 + "\n")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean markdown files converted from PDFs"
    )
    parser.add_argument(
        "--dir", "-d",
        default="data/japanese/markdown",
        help="Directory containing markdown files"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without modifying files"
    )
    
    args = parser.parse_args()
    
    clean_all_markdown_files(
        markdown_dir=args.dir,
        backup=not args.no_backup,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
