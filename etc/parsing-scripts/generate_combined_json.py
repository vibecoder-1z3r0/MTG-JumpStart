#!/usr/bin/env python3
"""
Generate a master combined JSON file with all JumpStart decks and card index.

Creates jumpstart-decks-combined.json with:
- All decks indexed by "SET:DECK_NAME"
- Card index for reverse lookups (which decks have card X?)
- Metadata about sets and deck counts

Usage:
    python generate_combined_json.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Base directory for set folders
BASE_DIR = Path(__file__).parent.parent

# All set directories
SETS = [
    "JMP", "J22", "J25", "TLA",
    "ONE", "DMU", "BRO", "MOM",
    "LTR", "CLU", "FDN", "TLB"
]

SET_NAMES = {
    "JMP": "JumpStart 2020",
    "J22": "JumpStart 2022",
    "J25": "JumpStart Foundations",
    "TLA": "Avatar: The Last Airbender",
    "ONE": "Phyrexia: All Will Be One",
    "DMU": "Dominaria United",
    "BRO": "The Brothers' War",
    "MOM": "March of the Machine",
    "LTR": "The Lord of the Rings",
    "CLU": "Ravnica: Clue Edition",
    "FDN": "Foundations Beginner Box",
    "TLB": "Avatar TLA Beginner Box"
}


def load_all_decks():
    """Load all individual deck JSON files."""
    all_decks = {}
    card_index = defaultdict(set)

    total_decks = 0

    for set_code in SETS:
        set_dir = BASE_DIR / set_code
        if not set_dir.exists():
            print(f"Warning: {set_code} directory not found", file=sys.stderr)
            continue

        json_files = sorted(set_dir.glob("*.json"))
        print(f"Processing {set_code}: {len(json_files)} decks", file=sys.stderr)

        for json_file in json_files:
            with open(json_file, 'r') as f:
                deck_data = json.load(f)

            deck_name = deck_data["deck_name"]
            deck_key = f"{set_code}:{deck_name}"

            # Store deck
            deck_entry = {
                "set": set_code,
                "set_name": SET_NAMES.get(set_code, set_code),
                "deck_name": deck_name,
                "tokens": deck_data.get("tokens", []),
                "cards": deck_data["cards"]
            }
            if deck_data.get("unofficial_tokens"):
                deck_entry["unofficial_tokens"] = deck_data["unofficial_tokens"]
            all_decks[deck_key] = deck_entry

            # Build card index
            for card in deck_data["cards"]:
                card_name = card["name"]
                card_index[card_name].add(deck_key)

            total_decks += 1

    # Convert sets to sorted lists for JSON serialization
    card_index_sorted = {
        card: sorted(list(decks))
        for card, decks in sorted(card_index.items())
    }

    return all_decks, card_index_sorted, total_decks


def generate_combined_json():
    """Generate the master combined JSON file."""
    print("Loading all deck files...", file=sys.stderr)
    all_decks, card_index, total_decks = load_all_decks()

    # Build metadata
    sets_with_counts = {
        set_code: len([k for k in all_decks.keys() if k.startswith(f"{set_code}:")])
        for set_code in SETS
    }

    # Build final structure
    combined = {
        "metadata": {
            "version": "1.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "total_decks": total_decks,
            "total_unique_cards": len(card_index),
            "sets": SETS,
            "set_names": SET_NAMES,
            "deck_counts": sets_with_counts
        },
        "decks": all_decks,
        "card_index": card_index
    }

    # Write to file
    output_file = BASE_DIR / "jumpstart-decks-combined.json"
    print(f"\nWriting combined JSON to {output_file}...", file=sys.stderr)

    with open(output_file, 'w') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    # Print statistics
    file_size = output_file.stat().st_size
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"✓ Generated: {output_file.name}", file=sys.stderr)
    print(f"  Total decks: {total_decks}", file=sys.stderr)
    print(f"  Unique cards: {len(card_index)}", file=sys.stderr)
    print(f"  File size: {file_size:,} bytes ({file_size/1024:.1f} KB)", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    return output_file


def main():
    """Main entry point."""
    try:
        output_file = generate_combined_json()
        print(f"\nSuccess! Combined JSON ready at:", file=sys.stderr)
        print(f"  {output_file}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
