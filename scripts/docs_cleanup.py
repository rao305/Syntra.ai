#!/usr/bin/env python3
"""
DAC Documentation Cleanup Script
Reorganizes all markdown files into a clean /docs structure.
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import yaml

# Configuration
REPO_ROOT = Path(__file__).parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
TODAY = datetime.now().strftime("%Y-%m-%d")

# File classification rules
KEEP_PATTERNS = [
    r"^README\.md$",
    r"^ARCHITECTURE\.md$",
    r"^SYSTEM_DESIGN\.md$",
    r"^API_REFERENCE\.md$",
    r"^CHANGELOG\.md$",
    r"^RELEASE_NOTES.*\.md$",
    r"^PHASE\d+_IMPLEMENTATION\.md$",
    r"^PHASE\d+_VALIDATION.*\.md$",
    r"^PHASE\d+_GO_NO_GO\.md$",
    r"^SECURITY\.md$",
    r"^CONTRIBUTING\.md$",
    r"^INTELLIGENT_ROUTING_GUIDE\.md$",
    r"^PROVIDER_SWITCHING_GUIDE\.md$",
    r"^QDRANT_SETUP_GUIDE\.md$",
    r"^TTFT_VERIFICATION_GUIDE\.md$",
    r"^ALERTING_GUIDE\.md$",
    r"^PROXY_SSE_CONFIG\.md$",
    r"^QUICK_START_GUIDE\.md$",
]

ARCHIVE_PATTERNS = [
    r".*notes.*\.md$",
    r".*log.*\.md$",
    r".*scratch.*\.md$",
    r".*debug.*\.md$",
    r".*_OLD\.md$",
    r".*_v\d+\.md$",
    r"backup_.*\.md$",
    r".*_RESULTS\.md$",
    r".*_STATUS\.md$",
    r".*_COMPLETE\.md$",
    r".*_SUMMARY\.md$",
    r".*_REPORT\.md$",
    r".*_TEST\.md$",
    r".*_CHECKLIST\.md$",  # Will override for validation checklists
    r".*_TEMPLATE\.md$",
    r"SPRINT_REPORT.*\.md$",
    r"EXPLORATION_REPORT\.md$",
    r"MODEL_SWITCHING_DEBUG\.md$",
    r"GEMINI_FIX\.md$",
    r"PERFORMANCE_FIX\.md$",
    r"SETUP_STATUS\.md$",
    r"COMPLETION_STATUS\.md$",
    r"READY_FOR_TESTING\.md$",
    r"PRE_TESTING_CHECKLIST\.md$",
]

# Mapping of old names to new standardized names
NAME_MAPPINGS = {
    "PHASE1_IMPLEMENTATION_COMPLETE.md": "PHASE1_IMPLEMENTATION.md",
    "PHASE2_WEEK1_COMPLETE.md": "PHASE2_IMPLEMENTATION.md",
    "PHASE3_PLAN.md": "PHASE3_IMPLEMENTATION.md",
    "PHASE4_IMPLEMENTATION.md": "PHASE4_IMPLEMENTATION.md",
    "PHASE4_1_VALIDATION_CHECKLIST.md": "PHASE4_1_VALIDATION_CHECKLIST.md",
    "RELEASE_NOTES_v0.1-phase1.md": "RELEASE_NOTES.md",
    "RELEASE_CHECKLIST_v0.1-phase1.md": "RELEASE_CHECKLIST.md",
}

# Track all changes
cleanup_report: List[Dict] = []


def should_keep(filename: str) -> bool:
    """Check if file should be kept (not archived)."""
    # Check explicit keep patterns
    for pattern in KEEP_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return True
    
    # Special cases
    if filename.startswith("PHASE") and "VALIDATION" in filename:
        return True
    if filename == "PHASE1_GO_NO_GO.md":
        return True
    
    return False


def should_archive(filename: str) -> bool:
    """Check if file should be archived."""
    if should_keep(filename):
        return False
    
    for pattern in ARCHIVE_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return True
    
    return False


def normalize_filename(filename: str) -> str:
    """Normalize filename to UPPER_SNAKE_CASE."""
    # Remove extension
    name, ext = os.path.splitext(filename)
    
    # Apply known mappings
    if filename in NAME_MAPPINGS:
        return NAME_MAPPINGS[filename]
    
    # Convert to UPPER_SNAKE_CASE
    # Remove version suffixes
    name = re.sub(r'[-_]v?\d+[-_]?.*$', '', name)
    name = re.sub(r'[-_]phase\d+[-_]?.*$', '', name, flags=re.IGNORECASE)
    
    # Replace hyphens and spaces with underscores
    name = name.replace('-', '_').replace(' ', '_')
    
    # Ensure uppercase
    name = name.upper()
    
    # Clean up multiple underscores
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    
    return f"{name}{ext}"


def extract_title_from_file(filepath: Path) -> str:
    """Extract title from first H1 in file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for front-matter title first
            frontmatter_match = re.search(r'^---\s*\ntitle:\s*(.+?)\s*\n', content, re.MULTILINE)
            if frontmatter_match:
                return frontmatter_match.group(1).strip('"\'')
            
            # Look for H1
            h1_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
            if h1_match:
                return h1_match.group(1).strip()
            
            # Fallback to filename
            name = filepath.stem.replace('_', ' ').title()
            return name
    except Exception:
        return filepath.stem.replace('_', ' ').title()


def add_frontmatter(filepath: Path, title: Optional[str] = None) -> bool:
    """Add or normalize front-matter in a markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if front-matter already exists
        if content.startswith('---'):
            # Parse existing front-matter
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if match:
                # Front-matter exists, ensure it has required fields
                fm_content = match.group(1)
                lines = fm_content.split('\n')
                fm_dict = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        fm_dict[key.strip()] = value.strip().strip('"\'')
                
                # Ensure required fields
                if 'title' not in fm_dict:
                    fm_dict['title'] = title or extract_title_from_file(filepath)
                if 'last_updated' not in fm_dict:
                    fm_dict['last_updated'] = TODAY
                if 'owner' not in fm_dict:
                    fm_dict['owner'] = 'DAC'
                if 'tags' not in fm_dict:
                    fm_dict['tags'] = ['dac', 'docs']
                
                # Reconstruct front-matter
                new_fm = yaml.dump(fm_dict, default_flow_style=False, sort_keys=False)
                new_content = f"---\n{new_fm}---\n\n{content[match.end():]}"
            else:
                # Malformed front-matter, replace it
                new_fm_dict = {
                    'title': title or extract_title_from_file(filepath),
                    'summary': 'Documentation file',
                    'last_updated': TODAY,
                    'owner': 'DAC',
                    'tags': ['dac', 'docs']
                }
                new_fm = yaml.dump(new_fm_dict, default_flow_style=False, sort_keys=False)
                new_content = f"---\n{new_fm}---\n\n{content}"
        else:
            # No front-matter, add it
            title = title or extract_title_from_file(filepath)
            fm_dict = {
                'title': title,
                'summary': 'Documentation file',
                'last_updated': TODAY,
                'owner': 'DAC',
                'tags': ['dac', 'docs']
            }
            new_fm = yaml.dump(fm_dict, default_flow_style=False, sort_keys=False)
            new_content = f"---\n{new_fm}---\n\n{content}"
        
        # Ensure H1 matches title
        title_from_fm = re.search(r'^title:\s*(.+?)$', new_content, re.MULTILINE)
        if title_from_fm:
            expected_title = title_from_fm.group(1).strip('"\'')
            # Check if first H1 matches
            h1_match = re.search(r'^#\s+(.+?)$', new_content, re.MULTILINE)
            if h1_match and h1_match.group(1).strip() != expected_title:
                # Replace H1 with title from front-matter
                new_content = re.sub(
                    r'^(#\s+)(.+?)$',
                    lambda m: f"{m.group(1)}{expected_title}",
                    new_content,
                    count=1,
                    flags=re.MULTILINE
                )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Warning: Could not add front-matter to {filepath}: {e}")
        return False


def find_all_md_files() -> List[Path]:
    """Find all markdown files in the repo (excluding node_modules, venv, .git)."""
    md_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__', '.next']]
        
        for file in files:
            if file.endswith('.md'):
                filepath = Path(root) / file
                # Skip files in venv or node_modules that weren't filtered
                if 'venv' in str(filepath) or 'node_modules' in str(filepath):
                    continue
                md_files.append(filepath)
    
    return md_files


def classify_file(filepath: Path) -> Tuple[str, Path]:
    """
    Classify a file and return (action, target_path).
    Actions: 'keep', 'archive', 'skip'
    """
    filename = filepath.name
    rel_path = filepath.relative_to(REPO_ROOT)
    
    # Skip root README.md (stays in root)
    if filename == "README.md" and filepath.parent == REPO_ROOT:
        return ('skip', filepath)
    
    # Skip files already in docs (we'll process them separately)
    if 'docs' in str(rel_path) and filepath.parent != REPO_ROOT:
        return ('skip', filepath)
    
    # Skip backend/frontend specific READMEs (keep in place)
    if filename == "README.md" and (filepath.parent.name in ['backend', 'frontend', 'apps']):
        return ('skip', filepath)
    
    # Classify
    if should_keep(filename):
        # Determine target location
        if filename.startswith("PHASE") and "IMPLEMENTATION" in filename:
            phase_num = re.search(r'PHASE(\d+)', filename)
            if phase_num:
                target = DOCS_ROOT / "PHASES" / f"PHASE{phase_num.group(1)}_IMPLEMENTATION.md"
            else:
                target = DOCS_ROOT / "PHASES" / normalize_filename(filename)
        elif filename.startswith("PHASE") and "VALIDATION" in filename:
            target = DOCS_ROOT / "PHASES" / "VALIDATION_CHECKLISTS" / normalize_filename(filename)
        elif filename in ["CHANGELOG.md", "RELEASE_NOTES.md"] or filename.startswith("RELEASE_"):
            if filename.startswith("RELEASE_NOTES"):
                target = DOCS_ROOT / "RELEASE_NOTES.md"
            elif filename.startswith("RELEASE_CHECKLIST"):
                target = DOCS_ROOT / "RELEASE_CHECKLIST.md"
            else:
                target = DOCS_ROOT / normalize_filename(filename)
        elif filename in ["ARCHITECTURE.md", "SYSTEM_DESIGN.md", "API_REFERENCE.md"]:
            target = DOCS_ROOT / normalize_filename(filename)
        elif filename in ["INTELLIGENT_ROUTING_GUIDE.md", "PROVIDER_SWITCHING_GUIDE.md", 
                          "QDRANT_SETUP_GUIDE.md", "TTFT_VERIFICATION_GUIDE.md",
                          "ALERTING_GUIDE.md", "PROXY_SSE_CONFIG.md", "QUICK_START_GUIDE.md"]:
            target = DOCS_ROOT / normalize_filename(filename)
        else:
            target = DOCS_ROOT / normalize_filename(filename)
        
        return ('keep', target)
    
    elif should_archive(filename):
        target = DOCS_ROOT / "archive" / normalize_filename(filename)
        return ('archive', target)
    
    else:
        # Unknown file, archive it to be safe
        target = DOCS_ROOT / "archive" / normalize_filename(filename)
        return ('archive', target)


def main():
    """Main cleanup function."""
    print("🔍 Discovering markdown files...")
    md_files = find_all_md_files()
    print(f"Found {len(md_files)} markdown files")
    
    # Filter to root-level files only for now
    root_files = [f for f in md_files if f.parent == REPO_ROOT]
    print(f"Processing {len(root_files)} root-level files")
    
    # Process each file
    for filepath in root_files:
        action, target = classify_file(filepath)
        
        if action == 'skip':
            continue
        
        # Create target directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle duplicates
        if target.exists() and target != filepath:
            # Merge or rename
            print(f"⚠️  Target exists: {target.name}, appending suffix")
            base = target.stem
            ext = target.suffix
            counter = 1
            while target.exists():
                target = target.parent / f"{base}_ALT{counter}{ext}"
                counter += 1
        
        # Copy file
        shutil.copy2(filepath, target)
        
        # Add front-matter
        title = extract_title_from_file(filepath)
        add_frontmatter(target, title)
        
        # Record change
        cleanup_report.append({
            'original': str(filepath.relative_to(REPO_ROOT)),
            'new': str(target.relative_to(REPO_ROOT)),
            'action': action,
            'rationale': f"Moved to {action} location"
        })
        
        print(f"✓ {action}: {filepath.name} → {target.name}")
    
    # Generate cleanup report
    report_path = DOCS_ROOT / "cleanup_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Documentation Cleanup Report\n\n")
        f.write(f"Generated: {TODAY}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total files processed: {len(cleanup_report)}\n")
        f.write(f"- Files kept: {len([r for r in cleanup_report if r['action'] == 'keep'])}\n")
        f.write(f"- Files archived: {len([r for r in cleanup_report if r['action'] == 'archive'])}\n\n")
        f.write("## File Changes\n\n")
        f.write("| Original Path | New Path | Action | Rationale |\n")
        f.write("|--------------|----------|--------|----------|\n")
        for entry in cleanup_report:
            f.write(f"| `{entry['original']}` | `{entry['new']}` | {entry['action']} | {entry['rationale']} |\n")
    
    print(f"\n✅ Cleanup complete! Report saved to {report_path}")
    print(f"📊 Processed {len(cleanup_report)} files")


if __name__ == "__main__":
    main()








