# The French Revolution: A History

The French Revolution: A History was written by the Scottish essayist, historian and philosopher Thomas Carlyle. The three-volume work, first published in 1837 (with a revised edition in print by 1857), charts the course of the French Revolution from 1789 to the height of the Reign of Terror (1793–94) and culminates in 1795.

## About This Repository

This repository contains a tool to convert Project Gutenberg ebook #1301 into a structured collection of markdown files, organized by volumes, books, and chapters.

## Quick Start

### Option 1: Use the Quick Start Script (Recommended)

```bash
./quick_start.sh
```

This script will:
1. Check for Python 3
2. Install dependencies automatically
3. Look for the HTML file or offer to download it
4. Run the conversion

### Option 2: Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Download and convert
python convert_gutenberg.py --download -o ./book

# Or convert from a local file
python convert_gutenberg.py -i 1301-h.htm -o ./book
```

### Usage

**Option 1: Download and convert automatically**
```bash
python convert_gutenberg.py --download -o ./book
```

**Option 2: Convert from a local HTML file**
```bash
# First, download the HTML version from Project Gutenberg:
# https://www.gutenberg.org/files/1301/1301-h/1301-h.htm

# Then run the converter:
python convert_gutenberg.py -i 1301-h.htm -o ./book
```

### Output Structure

The converter creates a directory structure like this:

```
book/
├── 01_the_bastille/
│   ├── 01_death_of_louis_xv/
│   │   ├── 01_louis_the_well_beloved.md
│   │   ├── 02_realized_ideals.md
│   │   ├── 03_viaticum.md
│   │   └── 04_louis_the_unforgotten.md
│   ├── 02_the_paper_age/
│   │   └── ...
│   └── ...
├── 02_the_constitution/
│   └── ...
└── 03_the_guillotine/
    └── ...
```

Each chapter is saved as a separate markdown file with:
- Chapter title as H1 heading
- Full chapter content with preserved formatting
- Footnotes section at the end

### Command-Line Options

```
usage: convert_gutenberg.py [-h] [--input FILE] [--output DIR] [--download] [--url URL]

Options:
  --input, -i FILE    Input HTML file path
  --output, -o DIR    Output directory (default: ./book)
  --download, -d      Download HTML from Project Gutenberg
  --url URL           Custom URL to download from
```

## Features

- ✅ Parses HTML structure into volumes, books, and chapters
- ✅ One markdown file per chapter
- ✅ Organized folder structure with numbered names
- ✅ Preserves footnotes
- ✅ Converts HTML formatting to markdown
- ✅ Handles both BeautifulSoup (recommended) and fallback parsing

## Requirements

- Python 3.6+
- beautifulsoup4 (recommended for better parsing)
- lxml (for HTML parsing)
