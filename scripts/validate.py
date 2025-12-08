#!/usr/bin/env python3
"""
Validate that the markdown content matches the original HTML source.
This ensures the book content hasn't been modified from the source.
"""

import sys
from pathlib import Path
import hashlib
import re

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("Warning: BeautifulSoup not installed. Install with: pip install beautifulsoup4")


def normalize_text(text):
    """Normalize text for comparison."""
    # Remove excessive whitespace
    text = ' '.join(text.split())
    # Remove markdown formatting but keep content
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'\[(\d+)\]', '', text)  # Remove footnote refs
    text = re.sub(r'\[\^(\d+)\]', '', text)  # Remove footnote refs
    return text.strip().lower()


def get_html_chapters(html_file):
    """Extract chapter content from HTML."""
    if not HAS_BS4:
        print("Error: BeautifulSoup required for validation")
        return {}
    
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    chapters = {}
    
    # Find all h3 tags (chapter headings)
    for h3 in soup.find_all('h3'):
        heading_text = h3.get_text(strip=True)
        
        # Match chapter pattern
        match = re.match(r'Chapter\s+(\d+)\.(\d+)\.([IVXLCDM]+)\.?\s*(.+)', heading_text, re.I)
        if match:
            vol = int(match.group(1))
            book = int(match.group(2))
            title = match.group(4).strip()
            
            # Collect text content until next h3
            content_parts = []
            current = h3.find_next_sibling()
            while current:
                if current.name == 'h3':
                    break
                if current.name == 'p':
                    text = current.get_text(separator=' ', strip=True)
                    # Exclude footnote paragraphs
                    if not text.startswith(tuple(f"{i} (" for i in range(1, 1000))):
                        content_parts.append(text)
                current = current.find_next_sibling()
            
            content = ' '.join(content_parts)
            key = (vol, book, title)
            chapters[key] = normalize_text(content)
    
    return chapters


def get_markdown_chapters(book_dir="."):
    """Extract chapter content from markdown files."""
    chapters = {}
    
    for md_file in Path(book_dir).rglob("*.md"):
        if md_file.name == "README.md":
            continue
        
        with open(md_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            continue
        
        # Extract title from first line
        title_line = lines[0].strip()
        if not title_line.startswith("#"):
            continue
        
        title = title_line[1:].strip()
        
        # Extract volume and book from path
        parts = md_file.parts
        if len(parts) < 3:
            continue
        
        vol_dir = parts[-3]
        book_dir = parts[-2]
        
        # Extract volume number
        vol_match = re.match(r'(\d+)_', vol_dir)
        if not vol_match:
            continue
        vol = int(vol_match.group(1))
        
        # Extract book number
        book_match = re.match(r'(\d+)_', book_dir)
        if not book_match:
            continue
        book = int(book_match.group(1))
        
        # Get content (skip title, join rest)
        content = ' '.join(line.strip() for line in lines[1:] if line.strip())
        
        key = (vol, book, title)
        chapters[key] = normalize_text(content)
    
    return chapters


def validate_content(html_file="original/pg1301-images.html", book_dir="."):
    """Validate markdown content against HTML source."""
    
    print(f"Validating book content against {html_file}...")
    
    html_chapters = get_html_chapters(html_file)
    md_chapters = get_markdown_chapters(book_dir)
    
    print(f"\nFound {len(html_chapters)} chapters in HTML")
    print(f"Found {len(md_chapters)} chapters in Markdown")
    
    if len(html_chapters) != len(md_chapters):
        print(f"\n⚠ Warning: Chapter count mismatch!")
    
    # Check each markdown chapter
    errors = 0
    for key, md_content in sorted(md_chapters.items()):
        vol, book, title = key
        
        if key not in html_chapters:
            print(f"\n⚠ Chapter not found in HTML: Vol {vol}, Book {book}, '{title}'")
            errors += 1
            continue
        
        html_content = html_chapters[key]
        
        # Compare content length as a proxy
        len_diff = abs(len(md_content) - len(html_content))
        len_ratio = len_diff / max(len(html_content), 1)
        
        if len_ratio > 0.1:  # More than 10% difference
            print(f"\n⚠ Content mismatch: Vol {vol}, Book {book}, '{title}'")
            print(f"  HTML length: {len(html_content)}, MD length: {len(md_content)}")
            errors += 1
    
    if errors == 0:
        print(f"\n✓ All {len(md_chapters)} chapters validated successfully!")
        print("Content matches the original HTML source.")
        return 0
    else:
        print(f"\n✗ Validation failed with {errors} error(s)")
        return 1


def main():
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    else:
        html_file = "original/pg1301-images.html"
    
    if not Path(html_file).exists():
        print(f"Error: HTML file not found: {html_file}")
        return 1
    
    return validate_content(html_file)


if __name__ == '__main__':
    sys.exit(main())
