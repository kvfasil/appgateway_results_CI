#!/usr/bin/env python3
"""
Automatically scan report directories and update index.html with the latest file structure.
"""

import os
import json
import re
from pathlib import Path

# Base directory - go up two levels from .github/scripts to repo root
BASE_DIR = Path(__file__).parent.parent.parent
INDEX_FILE = BASE_DIR / 'index.html'

def scan_reports():
    """Scan release and pr-test directories for HTML reports."""
    structure = {}
    
    # Scan release directory
    release_dir = BASE_DIR / 'release'
    if release_dir.exists():
        for version_dir in release_dir.iterdir():
            if version_dir.is_dir():
                for device_dir in version_dir.iterdir():
                    if device_dir.is_dir():
                        html_files = [
                            f.name for f in device_dir.iterdir() 
                            if f.is_file() and f.suffix == '.html' and f.name != 'index.html'
                        ]
                        if html_files:
                            key = f'release/{version_dir.name}/{device_dir.name}'
                            structure[key] = sorted(html_files)
    
    # Scan pr-test directory
    pr_test_dir = BASE_DIR / 'pr-test'
    if pr_test_dir.exists():
        for build_dir in pr_test_dir.iterdir():
            if build_dir.is_dir():
                for device_dir in build_dir.iterdir():
                    if device_dir.is_dir():
                        html_files = [
                            f.name for f in device_dir.iterdir() 
                            if f.is_file() and f.suffix == '.html' and f.name != 'index.html'
                        ]
                        if html_files:
                            key = f'pr-test/{build_dir.name}/{device_dir.name}'
                            structure[key] = sorted(html_files)
    
    return structure

def update_index_html(structure):
    """Update the file structure in index.html."""
    if not INDEX_FILE.exists():
        print(f"Error: {INDEX_FILE} not found")
        return False
    
    # Read current index.html
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create the new file structure JavaScript object
    file_structure_js = "        async function fetchFileListing(path) {\n"
    file_structure_js += "            const fileStructure = {\n"
    
    for path, files in sorted(structure.items()):
        files_str = json.dumps(files)
        file_structure_js += f"                '{path}': {files_str},\n"
    
    file_structure_js += "            };\n\n"
    file_structure_js += "            return fileStructure[path] || [];\n"
    file_structure_js += "        }"
    
    # Replace the fetchFileListing function
    # Pattern matches from comment through the entire function including closing brace
    pattern = r'        // Fetch file listing\n        async function fetchFileListing\(path\) \{[\s\S]*?\n        \}\n\n        // Extract report type'
    
    if not re.search(pattern, content):
        print("Error: Could not find fetchFileListing function pattern")
        return False
    
    new_content = re.sub(
        pattern,
        "        // Fetch file listing\n" + file_structure_js + "\n\n        // Extract report type",
        content
    )
    
    # Write updated content
    if new_content != content:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ index.html updated successfully")
        print(f"📊 Found {len(structure)} report locations")
        return True
    else:
        print("ℹ️  No changes needed")
        return False

def main():
    print("🔍 Scanning report directories...")
    structure = scan_reports()
    
    if not structure:
        print("⚠️  No reports found")
        return
    
    print(f"📁 Discovered reports:")
    for path, files in sorted(structure.items()):
        print(f"  {path}: {len(files)} file(s)")
    
    print("\n📝 Updating index.html...")
    update_index_html(structure)

if __name__ == '__main__':
    main()