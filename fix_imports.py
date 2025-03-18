#!/usr/bin/env python3
"""
Utility to fix common import issues in the Stone Email & Image Processor.
This script ensures all modules correctly import their dependencies.
"""
import os
import sys
import re
from pathlib import Path

def find_python_files(directory):
    """Find all Python files in the specified directory."""
    py_files = list(Path(directory).glob("*.py"))
    return [str(f) for f in py_files]

def check_import_references(file_path, all_files):
    """Check if a file has all necessary import statements."""
    file_basename = os.path.basename(file_path)
    module_name = os.path.splitext(file_basename)[0]
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all import statements
    import_pattern = re.compile(r'(?:from|import)\s+([a-zA-Z0-9_]+)')
    imports = set(match.group(1) for match in import_pattern.finditer(content))
    
    # Extract all references to other modules
    module_pattern = re.compile(r'(?<!\w)([a-zA-Z][a-zA-Z0-9_]*)\.')
    references = set(match.group(1) for match in module_pattern.finditer(content))
    
    # Find modules that are referenced but not imported
    missing_imports = references - imports - {'os', 'sys', 're', 'Path', 'time', 'json', 'datetime', 'pathlib'}
    
    return missing_imports

def add_missing_imports(file_path, missing_imports):
    """Add missing import statements to the file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find where imports end
    last_import_line = 0
    for i, line in enumerate(lines):
        if line.startswith(('import ', 'from ')):
            last_import_line = i
    
    # Add missing imports
    for module in missing_imports:
        if module == 'thread_utils' and 'ThreadIdentifier' in ''.join(lines):
            import_line = f"from thread_utils import ThreadIdentifier\n"
        else:
            import_line = f"import {module}\n"
        
        lines.insert(last_import_line + 1, import_line)
        print(f"Added import for '{module}' in {os.path.basename(file_path)}")
    
    # Write back the modified file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def fix_specific_issues(file_path):
    """Fix specific known issues in files."""
    file_basename = os.path.basename(file_path)
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # Fix email_processor.py issues
    if file_basename == 'email_processor.py':
        # Make sure update_thread_info is imported
        if 'from database import insert_email_data' in content and 'update_thread_info' not in content:
            content = content.replace(
                'from database import insert_email_data',
                'from database import insert_email_data, update_thread_info'
            )
            modified = True
            print(f"Fixed database import in {file_basename}")
    
    # Fix main.py issues
    if file_basename == 'main.py' and 'logger.info(f"Working directory: {os.getcwd()}")' in content and 'import os' not in content:
        content = content.replace('import sys', 'import sys\nimport os')
        modified = True
        print(f"Added missing os import in {file_basename}")
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return modified

def main():
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"Fixing imports in {script_dir}...")
    
    # Find all Python files
    py_files = find_python_files(script_dir)
    print(f"Found {len(py_files)} Python files")
    
    # Check each file for import issues
    for file_path in py_files:
        file_basename = os.path.basename(file_path)
        print(f"Checking {file_basename}...")
        
        # Fix specific known issues
        fixed = fix_specific_issues(file_path)
        
        # Check for missing imports
        missing_imports = check_import_references(file_path, py_files)
        if missing_imports:
            print(f"Found missing imports in {file_basename}: {', '.join(missing_imports)}")
            add_missing_imports(file_path, missing_imports)
        elif not fixed:
            print(f"No issues found in {file_basename}")
    
    print("\nImport fixing complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
