#!/usr/bin/env python3
"""
Generate Table of Contents for The French Revolution: A History
"""

import os
from pathlib import Path


def generate_toc(book_dir="."):
    """Generate table of contents from book structure."""
    
    # Volume names
    volumes = {
        "01_the_bastille": "The Bastille",
        "02_the_constitution": "The Constitution",
        "03_the_guillotine": "The Guillotine"
    }
    
    toc_lines = ["# The French Revolution: A History\n", "\n<!-- TOC START -->\n"]
    
    for vol_dir in sorted(Path(book_dir).glob("0*")):
        if not vol_dir.is_dir():
            continue
            
        vol_name = volumes.get(vol_dir.name, vol_dir.name.replace("_", " ").title())
        toc_lines.append(f"\n## {vol_name}\n")
        
        for book_dir_path in sorted(vol_dir.glob("0*")):
            if not book_dir_path.is_dir():
                continue
                
            # Get book name from directory
            book_name = book_dir_path.name.split("_", 1)[1].replace("_", " ").title()
            toc_lines.append(f"### {book_name}\n")
            
            for chapter_file in sorted(book_dir_path.glob("*.md")):
                # Read first line to get chapter title
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("# "):
                        title = first_line[2:].strip()
                    else:
                        title = chapter_file.stem.replace("_", " ").title()
                
                # Create relative path
                rel_path = chapter_file.relative_to(book_dir)
                toc_lines.append(f"- [{title}]({rel_path})\n")
    
    toc_lines.append("\n<!-- TOC END -->\n")
    return ''.join(toc_lines)


def main():
    toc = generate_toc()
    
    # Read existing README if it exists
    readme_path = Path("README.md")
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace TOC section
        if "<!-- TOC START -->" in content and "<!-- TOC END -->" in content:
            before = content.split("<!-- TOC START -->")[0]
            after = content.split("<!-- TOC END -->")[1]
            new_content = before + toc.split("<!-- TOC START -->")[1].split("<!-- TOC END -->")[0] + "<!-- TOC END -->" + after
        else:
            # Append TOC
            new_content = toc
    else:
        new_content = toc
    
    # Write README
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ Table of contents generated in README.md")
    print(f"  Total chapters indexed")


if __name__ == '__main__':
    main()
