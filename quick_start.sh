#!/bin/bash
# Quick start script for converting The French Revolution: A History

set -e

echo "=========================================="
echo "The French Revolution: A History"
echo "Gutenberg to Markdown Converter"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3.6 or later."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check if HTML file exists
HTML_FILE="1301-h.htm"
OUTPUT_DIR="book"

if [ -f "$HTML_FILE" ]; then
    echo ""
    echo "Found HTML file: $HTML_FILE"
    echo "Converting to markdown..."
    python3 convert_gutenberg.py -i "$HTML_FILE" -o "$OUTPUT_DIR"
else
    echo ""
    echo "HTML file not found: $HTML_FILE"
    echo ""
    echo "Please download it first:"
    echo "  1. Visit: https://www.gutenberg.org/files/1301/1301-h/1301-h.htm"
    echo "  2. Save the page as '1301-h.htm' in this directory"
    echo "  3. Run this script again"
    echo ""
    echo "Or try automatic download:"
    read -p "Attempt to download automatically? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Downloading..."
        if python3 convert_gutenberg.py --download -o "$OUTPUT_DIR"; then
            echo ""
            echo "✓ Download and conversion successful!"
        else
            echo ""
            echo "✗ Automatic download failed."
            echo "Please download manually as described above."
            exit 1
        fi
    else
        echo "Exiting. Please download the file manually."
        exit 0
    fi
fi

echo ""
echo "=========================================="
echo "✓ Conversion complete!"
echo "Output directory: $OUTPUT_DIR"
echo "=========================================="
