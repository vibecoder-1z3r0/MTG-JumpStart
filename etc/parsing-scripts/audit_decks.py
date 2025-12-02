#!/usr/bin/env python3
"""
Audit all deck lists for proper formatting and issues.

Checks:
1. Filename format (THEME NAME (1).txt vs THEME NAME-1.txt)
2. Unknown card entries (excluding "Random rare or mythic rare")
3. Deck name on first line matches filename
4. Card type headers present (//Creatures, //Lands, etc.)
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent
ETC_DIR = BASE_DIR / "etc"

# Track issues
issues = defaultdict(list)
stats = {
    'total_files': 0,
    'formatted': 0,
    'raw': 0,
    'bad_naming': 0,
    'unknown_cards': 0
}

def check_filename_format(filepath):
    """Check if filename follows standard format."""
    filename = filepath.stem

    # Check for hyphen format (bad)
    if re.search(r'-\d+$', filename):
        return f"Uses hyphen format: should be '{filename.replace('-', ' (')})'"

    # Check for number without space before parens (bad)
    if re.search(r'\w\(\d+\)$', filename):
        match = re.search(r'(\w)\((\d+)\)$', filename)
        if match:
            return f"Missing space before parens: should be '{filename[:match.start(1)+1]} ({match.group(2)})'"

    return None

def check_deck_content(filepath):
    """Check deck content for issues."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    if not lines:
        return "Empty file", None, []

    deck_name = lines[0].strip()
    expected_name = filepath.stem

    # Check if deck name matches filename
    name_issue = None
    if deck_name != expected_name:
        name_issue = f"Deck name '{deck_name}' doesn't match filename '{expected_name}'"

    # Check if formatted (has // headers)
    has_headers = any(line.strip().startswith('//') for line in lines)

    # Find Unknown entries (excluding "Random rare or mythic rare")
    unknown_cards = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line.startswith('//Unknown'):
            # This is a header, check what's under it
            for j in range(i, min(i+10, len(lines))):
                card_line = lines[j].strip()
                if card_line and not card_line.startswith('//'):
                    if 'random' not in card_line.lower() and 'rare' not in card_line.lower():
                        unknown_cards.append((i+j-i+1, card_line))

    return name_issue, has_headers, unknown_cards

def audit_directory(dir_path):
    """Audit all .txt files in a directory."""
    if not dir_path.is_dir():
        return

    set_name = dir_path.name
    txt_files = sorted(dir_path.glob("*.txt"))

    for filepath in txt_files:
        stats['total_files'] += 1

        # Check filename format
        filename_issue = check_filename_format(filepath)
        if filename_issue:
            issues['filename'].append(f"{set_name}/{filepath.name}: {filename_issue}")
            stats['bad_naming'] += 1

        # Check content
        name_issue, has_headers, unknown_cards = check_deck_content(filepath)

        if name_issue:
            issues['deck_name'].append(f"{set_name}/{filepath.name}: {name_issue}")

        if has_headers:
            stats['formatted'] += 1
        else:
            stats['raw'] += 1

        if unknown_cards:
            stats['unknown_cards'] += len(unknown_cards)
            for line_num, card in unknown_cards:
                issues['unknown'].append(f"{set_name}/{filepath.name}:{line_num}: {card}")

def main():
    print("=== DECK LIST AUDIT ===\n")

    # Audit each set directory
    for set_dir in sorted(ETC_DIR.iterdir()):
        if set_dir.is_dir() and set_dir.name not in ['parsing-scripts']:
            audit_directory(set_dir)

    # Print statistics
    print(f"Total files: {stats['total_files']}")
    print(f"Formatted: {stats['formatted']}")
    print(f"Raw: {stats['raw']}")
    print(f"Bad naming: {stats['bad_naming']}")
    print(f"Unknown cards: {stats['unknown_cards']}")
    print()

    # Print issues
    if issues['filename']:
        print("=== FILENAME FORMAT ISSUES ===")
        for issue in issues['filename']:
            print(f"  {issue}")
        print()

    if issues['deck_name']:
        print("=== DECK NAME MISMATCHES ===")
        for issue in issues['deck_name']:
            print(f"  {issue}")
        print()

    if issues['unknown']:
        print("=== UNKNOWN CARD ENTRIES ===")
        for issue in issues['unknown']:
            print(f"  {issue}")
        print()

    if not any(issues.values()):
        print("✓ No issues found!")

if __name__ == '__main__':
    main()
