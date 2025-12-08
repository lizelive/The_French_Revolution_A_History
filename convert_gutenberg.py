#!/usr/bin/env python3
"""
Convert Project Gutenberg ebook #1301 (The French Revolution: A History by Thomas Carlyle)
into markdown files organized by volumes, books, and chapters.

Usage:
    python convert_gutenberg.py --input <html_file> --output <output_dir>
    python convert_gutenberg.py --download --output <output_dir>
"""

import re
import sys
import argparse
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request
from typing import List, Dict, Optional
import html as html_module

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class Chapter:
    """Represents a chapter with its content and metadata."""
    
    def __init__(self, volume: int, book: int, chapter: int, title: str):
        self.volume = volume
        self.book = book
        self.chapter = chapter
        self.title = title.strip()
        self.content_paragraphs = []
        self.footnotes = []  # List of (number, text) tuples
        
    def add_paragraph(self, text: str):
        """Add a paragraph to the chapter."""
        text = text.strip()
        if text:
            self.content_paragraphs.append(text)
    
    def add_footnote(self, number: str, text: str):
        """Add a footnote to the chapter."""
        self.footnotes.append((number, text.strip()))
    
    def to_markdown(self) -> str:
        """Convert chapter to markdown format."""
        lines = []
        
        # Title as H1
        lines.append(f"# {self.title}\n")
        
        # Content paragraphs
        for para in self.content_paragraphs:
            lines.append(para)
            lines.append("")  # Blank line between paragraphs
        
        # Footnotes section
        if self.footnotes:
            lines.append("\n---\n")
            lines.append("## Footnotes\n")
            for num, text in self.footnotes:
                lines.append(f"[^{num}]: {text}\n")
        
        return '\n'.join(lines)
    
    def get_filename(self) -> str:
        """Generate filename for this chapter."""
        # Sanitize title for filename
        safe_title = slugify(self.title)
        return f"{self.chapter:02d}_{safe_title}.md"
    
    def get_volume_dir(self) -> str:
        """Get volume directory name."""
        volume_names = {
            1: "the_bastille",
            2: "the_constitution", 
            3: "the_guillotine"
        }
        vol_name = volume_names.get(self.volume, f"volume_{self.volume}")
        return f"{self.volume:02d}_{vol_name}"
    
    def get_book_dir(self) -> str:
        """Get book directory name."""
        # These are the actual book names from the table of contents
        book_names = {
            (1, 1): "death_of_louis_xv",
            (1, 2): "the_paper_age",
            (1, 3): "the_parlement_of_paris",
            (1, 4): "states_general",
            (1, 5): "the_third_estate",
            (1, 6): "consolidation",
            (1, 7): "the_insurrection_of_women",
            (2, 1): "the_feast_of_pikes",
            (2, 2): "nanci",
            (2, 3): "the_tuileries",
            (2, 4): "varennes",
            (2, 5): "parliament_first",
            (2, 6): "the_marseillese",
            (2, 7): "september",
            (3, 1): "september",
            (3, 2): "regicide",
            (3, 3): "the_girondins",
            (3, 4): "terror",
            (3, 5): "terror_the_guillotine",
            (3, 6): "thermidor",
            (3, 7): "vendemiaire"
        }
        key = (self.volume, self.book)
        book_name = book_names.get(key, f"book_{self.book}")
        return f"{self.book:02d}_{book_name}"


def slugify(text: str) -> str:
    """Convert text to a slug suitable for filenames."""
    # Remove HTML entities
    text = html_module.unescape(text)
    # Convert to ASCII
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Convert to lowercase and replace non-alphanumeric with underscore
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def roman_to_int(s: str) -> int:
    """Convert Roman numeral to integer."""
    if not s:
        return 0
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s = s.upper()
    total = 0
    prev_value = 0
    
    for char in reversed(s):
        value = roman_map.get(char, 0)
        if value >= prev_value:
            total += value
        else:
            total -= value
        prev_value = value
    
    return total


def html_to_markdown(element, preserve_links=True) -> str:
    """Convert HTML element to markdown text."""
    if isinstance(element, NavigableString):
        return str(element)
    
    if not hasattr(element, 'name'):
        return element.get_text()
    
    tag = element.name
    text = ''
    
    # Handle different tags
    if tag in ['p', 'div']:
        text = ''.join(html_to_markdown(child, preserve_links) for child in element.children)
    elif tag in ['em', 'i']:
        content = ''.join(html_to_markdown(child, preserve_links) for child in element.children)
        text = f"*{content}*"
    elif tag in ['strong', 'b']:
        content = ''.join(html_to_markdown(child, preserve_links) for child in element.children)
        text = f"**{content}**"
    elif tag == 'a' and preserve_links:
        content = ''.join(html_to_markdown(child, preserve_links) for child in element.children)
        href = element.get('href', '')
        if href.startswith('#footnote'):
            # Footnote reference
            text = f"[^{content.strip('[]')}]"
        else:
            text = content
    elif tag == 'br':
        text = '\n'
    else:
        text = ''.join(html_to_markdown(child, preserve_links) for child in element.children)
    
    return text


def parse_with_beautifulsoup(html_content: str) -> List[Chapter]:
    """Parse HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_content, 'html.parser')
    chapters = []
    
    # Remove script and style tags
    for tag in soup(['script', 'style']):
        tag.decompose()
    
    # Find all headings (h1-h6) to identify structure
    all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    current_volume = 0
    current_book = 0
    current_chapter = None
    footnote_map = {}
    
    # First pass: collect footnotes
    for footnote_div in soup.find_all(['div', 'p'], class_=re.compile(r'footnote', re.I)):
        footnote_text = footnote_div.get_text(strip=True)
        # Try to extract footnote number and text
        match = re.match(r'\[(\d+)\]\s*(.*)', footnote_text)
        if match:
            footnote_map[match.group(1)] = match.group(2)
    
    # Also look for footnotes at the end or in specific sections
    for elem in soup.find_all('p'):
        text = elem.get_text(strip=True)
        if re.match(r'^\[\d+\]', text):
            match = re.match(r'^\[(\d+)\]\s*(.*)', text)
            if match:
                footnote_map[match.group(1)] = match.group(2)
    
    # Second pass: parse chapters
    for heading in all_headings:
        heading_text = heading.get_text(strip=True)
        
        # Check for VOLUME markers
        vol_match = re.match(r'VOLUME\s+([IVX]+)', heading_text, re.I)
        if vol_match:
            current_volume = roman_to_int(vol_match.group(1))
            continue
        
        # Check for BOOK markers (format: "BOOK 1.2. Title" or "BOOK 1.2—Title")
        book_match = re.match(r'BOOK\s+(\d+)\.(\d+)[\.\s—-]*(.+)?', heading_text, re.I)
        if book_match:
            current_volume = int(book_match.group(1))
            current_book = int(book_match.group(2))
            continue
        
        # Check for CHAPTER markers (format: "CHAPTER 1.1.IV. Title")
        chapter_match = re.match(
            r'CHAPTER\s+(\d+)\.(\d+)\.([IVX]+)[\.\s—-]*(.+)',
            heading_text,
            re.I
        )
        if chapter_match:
            # Save previous chapter
            if current_chapter:
                chapters.append(current_chapter)
            
            # Create new chapter
            vol = int(chapter_match.group(1))
            book = int(chapter_match.group(2))
            chap_roman = chapter_match.group(3)
            chap_num = roman_to_int(chap_roman)
            title = chapter_match.group(4).strip()
            
            current_chapter = Chapter(vol, book, chap_num, title)
            
            # Collect content until next chapter
            current_elem = heading.find_next_sibling()
            chapter_footnote_refs = set()
            
            while current_elem:
                # Stop at next heading that might be a chapter/book/volume
                if current_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    next_text = current_elem.get_text(strip=True)
                    if re.match(r'(VOLUME|BOOK|CHAPTER)\s+', next_text, re.I):
                        break
                
                # Add paragraph content
                if current_elem.name == 'p':
                    para_text = html_to_markdown(current_elem)
                    if para_text.strip():
                        current_chapter.add_paragraph(para_text)
                        # Find footnote references in markdown format [^1], [^2], etc.
                        footnote_refs = re.findall(r'\[\^(\d+)\]', para_text)
                        chapter_footnote_refs.update(footnote_refs)
                        # Also check for plain [1] style that might not have been converted
                        # Only match if not preceded by ^ to avoid double-counting
                        footnote_refs_plain = re.findall(r'(?<!\^)\[(\d+)\]', para_text)
                        chapter_footnote_refs.update(footnote_refs_plain)
                
                current_elem = current_elem.find_next_sibling()
            
            # Add only referenced footnotes to chapter
            for num in sorted(chapter_footnote_refs, key=lambda x: int(x) if x.isdigit() else 0):
                if num in footnote_map:
                    current_chapter.add_footnote(num, footnote_map[num])
    
    # Don't forget last chapter
    if current_chapter:
        chapters.append(current_chapter)
    
    return chapters


def parse_without_beautifulsoup(html_content: str) -> List[Chapter]:
    """Parse HTML without BeautifulSoup (fallback method)."""
    chapters = []
    lines = html_content.split('\n')
    
    current_volume = 0
    current_book = 0
    current_chapter = None
    in_chapter_content = False
    footnotes = {}
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Remove HTML tags for text analysis
        clean_line = re.sub(r'<[^>]+>', '', line)
        
        # Check for volume
        vol_match = re.search(r'VOLUME\s+([IVX]+)', clean_line, re.I)
        if vol_match:
            current_volume = roman_to_int(vol_match.group(1))
            i += 1
            continue
        
        # Check for book
        book_match = re.search(r'BOOK\s+(\d+)\.(\d+)', clean_line, re.I)
        if book_match:
            current_volume = int(book_match.group(1))
            current_book = int(book_match.group(2))
            i += 1
            continue
        
        # Check for chapter
        chapter_match = re.search(
            r'CHAPTER\s+(\d+)\.(\d+)\.([IVX]+)[\.\s—-]*(.+)',
            clean_line,
            re.I
        )
        if chapter_match:
            # Save previous chapter
            if current_chapter:
                chapters.append(current_chapter)
            
            # Create new chapter
            vol = int(chapter_match.group(1))
            book = int(chapter_match.group(2))
            chap_roman = chapter_match.group(3)
            chap_num = roman_to_int(chap_roman)
            title = chapter_match.group(4).strip()
            
            current_chapter = Chapter(vol, book, chap_num, title)
            in_chapter_content = True
            i += 1
            continue
        
        # Collect chapter content
        if in_chapter_content and current_chapter:
            # Check if this is a paragraph
            if '<p>' in line or '<p ' in line:
                # Extract text from paragraph
                para_text = re.sub(r'<[^>]+>', '', line)
                para_text = html_module.unescape(para_text).strip()
                if para_text:
                    current_chapter.add_paragraph(para_text)
        
        # Check for footnotes
        footnote_match = re.search(r'\[(\d+)\]\s*(.+)', clean_line)
        if footnote_match:
            footnotes[footnote_match.group(1)] = footnote_match.group(2)
        
        i += 1
    
    # Add footnotes to all chapters
    for chapter in chapters:
        for num, text in footnotes.items():
            chapter.add_footnote(num, text)
    
    # Don't forget last chapter
    if current_chapter and current_chapter not in chapters:
        chapters.append(current_chapter)
    
    return chapters


def download_html(url: str) -> str:
    """Download HTML content from URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:
        return response.read().decode('utf-8', errors='ignore')


def convert_to_markdown(html_file: str, output_dir: str):
    """Main conversion function."""
    print(f"Reading HTML file: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()
    
    print("Parsing book structure...")
    
    if HAS_BS4:
        print("Using BeautifulSoup parser")
        chapters = parse_with_beautifulsoup(html_content)
    else:
        print("Using fallback parser (install beautifulsoup4 for better results)")
        chapters = parse_without_beautifulsoup(html_content)
    
    print(f"Found {len(chapters)} chapters")
    
    if not chapters:
        print("\nError: No chapters found!")
        print("The HTML file might not be in the expected format.")
        print("Expected chapter headings like: 'CHAPTER 1.1.IV. Title'")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Write chapters to files
    chapter_count = 0
    for chapter in chapters:
        # Create directory structure
        volume_dir = output_path / chapter.get_volume_dir()
        book_dir = volume_dir / chapter.get_book_dir()
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Write chapter file
        chapter_file = book_dir / chapter.get_filename()
        print(f"Writing: {chapter_file}")
        
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(chapter.to_markdown())
        
        chapter_count += 1
    
    print(f"\n✓ Conversion complete!")
    print(f"  Chapters written: {chapter_count}")
    print(f"  Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Project Gutenberg ebook #1301 to structured markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert from local HTML file
  python convert_gutenberg.py -i pg1301.html -o ./book
  
  # Download and convert
  python convert_gutenberg.py --download -o ./book
  
  # Use custom URL
  python convert_gutenberg.py --url http://example.com/book.html -o ./book
        """
    )
    parser.add_argument(
        '--input', '-i',
        help='Input HTML file path',
        metavar='FILE'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory for markdown files (default: ./book)',
        default='./book',
        metavar='DIR'
    )
    parser.add_argument(
        '--download', '-d',
        action='store_true',
        help='Download HTML from Project Gutenberg'
    )
    parser.add_argument(
        '--url',
        help='Custom URL to download from',
        default='https://www.gutenberg.org/files/1301/1301-h/1301-h.htm',
        metavar='URL'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.input and not args.download:
        parser.error("Either --input or --download must be specified")
    
    # Get HTML file
    html_file = args.input
    
    if args.download:
        print(f"Downloading from {args.url}...")
        try:
            html_content = download_html(args.url)
            # Use cross-platform temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                html_file = f.name
            print(f"✓ Downloaded to {html_file}")
        except Exception as e:
            print(f"✗ Error downloading: {e}")
            print("\nPlease download the HTML file manually:")
            print(f"  1. Visit: {args.url}")
            print("  2. Save the page as HTML")
            print("  3. Run: python convert_gutenberg.py -i <saved_file> -o ./book")
            sys.exit(1)
    
    # Convert
    try:
        convert_to_markdown(html_file, args.output)
    except Exception as e:
        print(f"\n✗ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
