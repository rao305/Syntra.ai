#!/usr/bin/env python3
"""Replace print() statements with logger calls."""

import re
import sys
from pathlib import Path

def has_logger_import(content):
    """Check if file already has logger import."""
    return "logger = logging.getLogger" in content or "import logging" in content

def add_logger_import(content):
    """Add logger import if not present."""
    if has_logger_import(content):
        return content

    # Find the last import line
    lines = content.split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    # Insert logging imports after last import
    if "import logging" not in content:
        lines.insert(last_import_idx + 1, "import logging")

    if "logger = logging.getLogger" not in content:
        lines.insert(last_import_idx + 2, "logger = logging.getLogger(__name__)")

    return '\n'.join(lines)

def convert_print_to_logger(match):
    """Convert print() call to logger.info()."""
    indent = match.group(1)
    content = match.group(2)

    # Determine log level based on content
    content_lower = content.lower()
    if '✅' in content or 'success' in content_lower or 'initialized' in content_lower:
        level = 'info'
    elif '⚠️' in content or 'warning' in content_lower or 'failed' in content_lower:
        level = 'warning'
    elif '❌' in content or 'error' in content_lower:
        level = 'error'
    elif '🔍' in content or 'debug' in content_lower:
        level = 'debug'
    else:
        level = 'info'

    return f'{indent}logger.{level}({content})'

def fix_file(filepath):
    """Fix print statements in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add logger import if needed
    content = add_logger_import(content)

    # Replace print() calls with logger calls
    # Pattern: whitespace + print( + anything + )
    pattern = r'(\s*)print\((.+?)\)(?=\n)'
    fixed = re.sub(pattern, convert_print_to_logger, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(fixed)

    return fixed != content

# Files to fix
files_to_fix = [
    '/Users/rao305/Documents/Syntra/backend/app/api/threads.py',
    '/Users/rao305/Documents/Syntra/backend/app/services/threads_store.py',
    '/Users/rao305/Documents/Syntra/backend/app/services/context_builder.py'
]

print("Fixing print statements...")
for filepath in files_to_fix:
    p = Path(filepath)
    if p.exists():
        if fix_file(filepath):
            print(f"✅ Fixed {filepath}")
        else:
            print(f"⚠️  No changes needed for {filepath}")
    else:
        print(f"❌ File not found: {filepath}")

print("\n✅ All print statements have been converted to logger calls!")
