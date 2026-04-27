#!/usr/bin/env python3
"""
Generate JSON deck files from TXT deck lists with full card data from cache.

Creates {deck_name}.json files alongside each {deck_name}.txt file in the set directories.

Usage:
    python generate_json_decks.py ../JMP/ ../J22/ ../J25/
    python generate_json_decks.py ../*/  # All sets
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Cache file location
CACHE_FILE = Path(__file__).parent / "card_type_cache.json"


def load_cache() -> Dict:
    """Load card data cache from disk."""
    if not CACHE_FILE.exists():
        print(f"Error: Cache file not found: {CACHE_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)

    # Remove metadata fields
    cache = {k: v for k, v in cache.items() if not k.startswith('_')}

    print(f"Loaded {len(cache)} cards from cache", file=sys.stderr)
    return cache


def parse_card_line(line: str) -> Tuple[int, str]:
    """
    Parse a card line to extract quantity and card name.

    Returns: (quantity, card_name)
    """
    line = line.strip()

    # Try to parse quantity
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[0].isdigit():
        quantity = int(parts[0])
        card_name = parts[1].strip()
    else:
        quantity = 1
        card_name = line.strip()

    return (quantity, card_name)


def generate_json_from_txt(txt_file: Path, cache: Dict) -> Dict:
    """
    Generate JSON deck data from a TXT deck file.

    Returns a dict with deck_name, set, and cards array.
    """
    # Read TXT file
    with open(txt_file, 'r') as f:
        lines = f.readlines()

    # Extract deck name and set
    deck_name = txt_file.stem
    set_code = txt_file.parent.name

    # Parse cards
    cards = []

    for line in lines:
        line = line.strip()

        # Skip empty lines, deck name, section headers, and comments
        if not line or line.startswith('//') or line == deck_name:
            continue

        # Parse card
        quantity, card_name = parse_card_line(line)

        # Look up card in cache
        card_data = cache.get(card_name, {})

        # Build card entry
        card_entry = {
            "quantity": quantity,
            "name": card_name
        }

        # Add cached data if available
        if card_data:
            # Always include type
            card_entry["type"] = card_data.get("type", "Unknown")

            # Add other fields if they exist
            if "type_line" in card_data:
                card_entry["type_line"] = card_data["type_line"]
            if "mana_cost" in card_data:
                card_entry["mana_cost"] = card_data["mana_cost"]
            if "cmc" in card_data:
                card_entry["cmc"] = card_data["cmc"]
            if "colors" in card_data:
                card_entry["colors"] = card_data["colors"]
            if "rarity" in card_data:
                card_entry["rarity"] = card_data["rarity"]

            # Creature-specific fields
            if "power" in card_data and card_data["power"] is not None:
                card_entry["power"] = card_data["power"]
            if "toughness" in card_data and card_data["toughness"] is not None:
                card_entry["toughness"] = card_data["toughness"]

            # Planeswalker-specific fields
            if "loyalty" in card_data and card_data["loyalty"] is not None:
                card_entry["loyalty"] = card_data["loyalty"]

            # Token data — only include if card actually creates tokens
            if card_data.get("tokens"):
                card_entry["tokens"] = card_data["tokens"]
            # Unofficial tokens — created by card text but no official printed token card
            if card_data.get("unofficial_tokens"):
                card_entry["unofficial_tokens"] = card_data["unofficial_tokens"]
        else:
            # Card not in cache
            card_entry["type"] = "Unknown"

        cards.append(card_entry)

    # Aggregate deck-level tokens: deduplicated by name, sorted alphabetically.
    # If two cards create tokens with the same name, the first one's data is used.
    seen_token_names: dict = {}
    for card in cards:
        for token in card.get("tokens", []):
            name = token["name"]
            if name not in seen_token_names:
                seen_token_names[name] = token
    deck_tokens = sorted(seen_token_names.values(), key=lambda t: t["name"])

    # Aggregate deck-level unofficial tokens (same dedup logic).
    seen_unofficial_names: dict = {}
    for card in cards:
        for token in card.get("unofficial_tokens", []):
            name = token["name"]
            if name not in seen_unofficial_names:
                seen_unofficial_names[name] = token
    deck_unofficial_tokens = sorted(seen_unofficial_names.values(), key=lambda t: t["name"])

    # Build final structure
    deck_json = {
        "deck_name": deck_name,
        "set": set_code,
        "tokens": deck_tokens,
        "cards": cards
    }
    if deck_unofficial_tokens:
        deck_json["unofficial_tokens"] = deck_unofficial_tokens

    return deck_json


def process_directory(directory: Path, cache: Dict, dry_run: bool = False) -> int:
    """
    Process all TXT files in a directory and generate JSON files.

    Returns count of files generated.
    """
    if not directory.exists() or not directory.is_dir():
        print(f"Error: Not a valid directory: {directory}", file=sys.stderr)
        return 0

    # Find all .txt files
    txt_files = sorted(directory.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {directory}", file=sys.stderr)
        return 0

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SET: {directory.name} - Processing {len(txt_files)} decks", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    generated_count = 0

    for txt_file in txt_files:
        # Generate JSON
        deck_json = generate_json_from_txt(txt_file, cache)

        # Output file path
        json_file = txt_file.with_suffix('.json')

        if dry_run:
            print(f"  [DRY RUN] Would create: {json_file.name}", file=sys.stderr)
        else:
            # Write JSON file (pretty-printed)
            with open(json_file, 'w') as f:
                json.dump(deck_json, f, indent=2, ensure_ascii=False)

            print(f"  ✓ Generated: {json_file.name} ({len(deck_json['cards'])} cards)", file=sys.stderr)
            generated_count += 1

    print(f"\n{directory.name}: {generated_count}/{len(txt_files)} JSON files generated", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    return generated_count


def main():
    """Main entry point."""
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]

    dry_run = '--dry-run' in sys.argv

    if not args:
        print("Usage: python generate_json_decks.py <directory> [<directory> ...]", file=sys.stderr)
        print("\nOptions:", file=sys.stderr)
        print("  --dry-run    Preview what would be generated without creating files", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  python generate_json_decks.py ../JMP/ ../J22/", file=sys.stderr)
        print("  python generate_json_decks.py ../*/  # All sets", file=sys.stderr)
        return 1

    if dry_run:
        print("=== DRY RUN MODE - No files will be created ===\n", file=sys.stderr)

    # Load cache
    cache = load_cache()

    # Process each directory
    total_generated = 0
    for dir_path in args:
        directory = Path(dir_path)
        total_generated += process_directory(directory, cache, dry_run)

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"✓ COMPLETE! Generated {total_generated} JSON files", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
