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
    file_structure = {}
    dir_structure = {}
    
    # Scan release directory
    release_dir = BASE_DIR / 'release'
    release_versions = []
    if release_dir.exists():
        for version_dir in release_dir.iterdir():
            if version_dir.is_dir():
                release_versions.append(version_dir.name)
                devices = []
                for device_dir in version_dir.iterdir():
                    if device_dir.is_dir():
                        devices.append(device_dir.name)
                        html_files = [
                            f.name for f in device_dir.iterdir() 
                            if f.is_file() and f.suffix == '.html' and f.name != 'index.html'
                        ]
                        if html_files:
                            key = f'release/{version_dir.name}/{device_dir.name}'
                            file_structure[key] = sorted(html_files)
                if devices:
                    dir_structure[f'release/{version_dir.name}'] = sorted(devices)
    if release_versions:
        dir_structure['release'] = sorted(release_versions)
    
    # Scan pr-test directory
    pr_test_dir = BASE_DIR / 'pr-test'
    pr_test_builds = []
    if pr_test_dir.exists():
        for build_dir in pr_test_dir.iterdir():
            if build_dir.is_dir():
                pr_test_builds.append(build_dir.name)
                devices = []
                for device_dir in build_dir.iterdir():
                    if device_dir.is_dir():
                        devices.append(device_dir.name)
                        html_files = [
                            f.name for f in device_dir.iterdir() 
                            if f.is_file() and f.suffix == '.html' and f.name != 'index.html'
                        ]
                        if html_files:
                            key = f'pr-test/{build_dir.name}/{device_dir.name}'
                            file_structure[key] = sorted(html_files)
                if devices:
                    dir_structure[f'pr-test/{build_dir.name}'] = sorted(devices)
    if pr_test_builds:
        dir_structure['pr-test'] = sorted(pr_test_builds)
    
    return file_structure, dir_structure

def update_index_html(file_structure, dir_structure):
    """Update the file structure and directory structure in index.html."""
    if not INDEX_FILE.exists():
        print(f"Error: {INDEX_FILE} not found")
        return False
    
    # Read current index.html
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create the new directory structure JavaScript object
    dir_structure_js = "        async function fetchDirectoryListing(path) {\n"
    dir_structure_js += "            const structure = {\n"
    
    for path, dirs in sorted(dir_structure.items()):
        dirs_str = json.dumps(dirs)
        dir_structure_js += f"                '{path}': {dirs_str},\n"
    
    dir_structure_js += "            };\n\n"
    dir_structure_js += "            return structure[path] || [];\n"
    dir_structure_js += "        }"
    
    # Create the new file structure JavaScript object
    file_structure_js = "        async function fetchFileListing(path) {\n"
    file_structure_js += "            const fileStructure = {\n"
    
    for path, files in sorted(file_structure.items()):
        files_str = json.dumps(files)
        file_structure_js += f"                '{path}': {files_str},\n"
    
    file_structure_js += "            };\n\n"
    file_structure_js += "            return fileStructure[path] || [];\n"
    file_structure_js += "        }"
    
    # Replace the fetchDirectoryListing function
    dir_pattern = r'        async function fetchDirectoryListing\(path\) \{[\s\S]*?\n        \}\n\n        // Fetch file listing'
    
    if not re.search(dir_pattern, content):
        print("Error: Could not find fetchDirectoryListing function pattern")
        return False
    
    content = re.sub(
        dir_pattern,
        dir_structure_js + "\n\n        // Fetch file listing",
        content
    )
    
    # Replace the fetchFileListing function
    file_pattern = r'        // Fetch file listing\n        async function fetchFileListing\(path\) \{[\s\S]*?\n        \}\n\n        // Extract report type'
    
    if not re.search(file_pattern, content):
        print("Error: Could not find fetchFileListing function pattern")
        return False
    
    new_content = re.sub(
        file_pattern,
        "        // Fetch file listing\n" + file_structure_js + "\n\n        // Extract report type",
        content
    )
    
    # Write updated content
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ index.html updated successfully")
    print(f"📊 Found {len(file_structure)} report locations")
    return True

def main():
    print("🔍 Scanning report directories...")
    file_structure, dir_structure = scan_reports()
    
    if not file_structure:
        print("⚠️  No reports found")
        return
    
    print(f"📁 Discovered reports:")
    for path, files in sorted(file_structure.items()):
        print(f"  {path}: {len(files)} file(s)")
    
    print("\n📝 Updating index.html...")
    update_index_html(file_structure, dir_structure)

if __name__ == '__main__':
    main()