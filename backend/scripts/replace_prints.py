"""
Script to automatically replace print() statements with proper logging.
Run this script to fix all debug prints in the codebase.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Patterns to match and replace
PRINT_PATTERNS = [
    # Simple print statements
    (r'print\(f?"([^"]*debug[^"]*)"\)', r'logger.debug("\1")'),
    (r'print\(f?"([^"]*error[^"]*)"\)', r'logger.error("\1")'),
    (r'print\(f?"([^"]*warn[^"]*)"\)', r'logger.warning("\1")'),
    (r"print\(f? '([^']*debug[^']*)'\)", r'logger.debug("\1")'),
    (r"print\(f?'([^']*error[^']*)'\)", r'logger.error("\1")'),

    # Print with emoji indicators
    (r'print\(f?"✅([^"]*)"\)', r'logger.info("✅\1")'),
    (r'print\(f?"❌([^"]*)"\)', r'logger.error("❌\1")'),
    (r'print\(f?"⚠️([^"]*)"\)', r'logger.warning("⚠️\1")'),
    (r'print\(f?"🔍([^"]*)"\)', r'logger.debug("🔍\1")'),

    # Generic prints (convert to info)
    (r'print\(f?"([^"]*)"\)', r'logger.info("\1")'),
    (r"print\(f? '([^']*)'\)", r'logger.info("\1")'),
]

# Import statement to add
LOGGING_IMPORT = "import logging\nlogger = logging.getLogger(__name__)\n"

def process_file(filepath: Path) -> Tuple[int, List[str]]:
    """Process a single Python file and replace prints with logging."""
    changes = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Check if logging is already imported
    has_logging_import = "import logging" in content or "from logging import" in content
    has_logger = "logger = logging.getLogger" in content or "logger = getLogger" in content

    # Apply replacements
    for pattern, replacement in PRINT_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            changes.extend(matches)

    # Add logging import if needed and changes were made
    if changes and not has_logging_import:
        # Find the right place to insert (after other imports)
        import_section_end = 0
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_section_end = i

        lines.insert(import_section_end + 1, "")
        lines.insert(import_section_end + 2, "import logging")
        if not has_logger:
            lines.insert(import_section_end + 3, 'logger = logging.getLogger(__name__)')
        content = "\n".join(lines)

    # Write changes if any
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return len(changes), changes


def main():
    """Main entry point."""
    backend_path = Path(__file__).parent.parent / "app"

    total_changes = 0
    files_changed = 0

    print("Scanning for print statements...\n")

    for py_file in backend_path.rglob("*.py"):
        # Skip __pycache__ and migrations
        if "__pycache__" in str(py_file) or "migrations" in str(py_file):
            continue

        num_changes, changes = process_file(py_file)

        if num_changes > 0:
            print(f"📝 {py_file.relative_to(backend_path)}: {num_changes} prints replaced")
            files_changed += 1
            total_changes += num_changes

    print(f"\n✅ Complete! Replaced {total_changes} print statements in {files_changed} files.")
    print("\n⚠️  Please review the changes and ensure logging levels are appropriate.")


if __name__ == "__main__":
    main()
