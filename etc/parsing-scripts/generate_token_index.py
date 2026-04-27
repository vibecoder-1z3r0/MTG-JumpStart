#!/usr/bin/env python3
"""
generate_token_index.py - Build a consolidated token reference from all deck JSONs.

Scans all deck JSON files across every set, collects token data, deduplicates
by oracle_id (falling back to name+type_line), and records which cards and
decks in which sets produce each token.

Output: etc/jumpstart-token-index.json

Usage:
    python generate_token_index.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

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
    "TLB": "Avatar TLA Beginner Box",
}


def token_key(token: dict) -> str:
    """
    Unique key for deduplicating tokens.
    Prefer oracle_id (Scryfall's canonical identity); fall back to
    name + type_line + power/toughness so differently-statted tokens
    with the same name (e.g. 1/1 Warrior vs 2/2 Warrior) stay separate.
    """
    if token.get("oracle_id"):
        return token["oracle_id"]
    p = token.get("power", "")
    t = token.get("toughness", "")
    return f"{token.get('name','')}|{token.get('type_line','')}|{p}/{t}"


def merge_token_data(existing: dict, incoming: dict) -> dict:
    """
    Fill in any missing fields on an existing token entry from a newer
    sighting — useful when early sightings lack keywords/oracle_id.
    """
    for field in ("colors", "power", "toughness", "keywords", "oracle_id", "type_line"):
        if field not in existing and field in incoming:
            existing[field] = incoming[field]
        elif field == "keywords" and not existing.get("keywords") and incoming.get("keywords"):
            existing["keywords"] = incoming["keywords"]
    return existing


def main():
    print("Scanning deck JSON files...", file=sys.stderr)

    # token_key → { token fields + "sources": [...] }
    token_map: dict = {}
    # token_key → set of (set, deck, card) tuples to deduplicate sources
    seen_sources: dict = defaultdict(set)

    total_decks = 0
    total_source_refs = 0

    for set_code in SETS:
        set_dir = BASE_DIR / set_code
        if not set_dir.exists():
            print(f"  Warning: {set_code} directory not found", file=sys.stderr)
            continue

        json_files = sorted(set_dir.glob("*.json"))
        set_name = SET_NAMES.get(set_code, set_code)
        print(f"  {set_code}: {len(json_files)} decks", file=sys.stderr)

        for json_file in json_files:
            with open(json_file) as f:
                deck = json.load(f)

            deck_name = deck.get("deck_name", json_file.stem)
            total_decks += 1

            for card in deck.get("cards", []):
                for token in card.get("tokens", []):
                    key = token_key(token)

                    # Register token if new
                    if key not in token_map:
                        entry: dict = {
                            "name": token.get("name", ""),
                            "type_line": token.get("type_line", ""),
                        }
                        if "colors" in token:
                            entry["colors"] = token["colors"]
                        if "power" in token:
                            entry["power"] = token["power"]
                        if "toughness" in token:
                            entry["toughness"] = token["toughness"]
                        if token.get("keywords") is not None:
                            entry["keywords"] = token["keywords"]
                        if token.get("oracle_id"):
                            entry["oracle_id"] = token["oracle_id"]
                        entry["sources"] = []
                        token_map[key] = entry
                    else:
                        merge_token_data(token_map[key], token)

                    # Add source reference (deduplicated per set+deck+card)
                    source_sig = (set_code, deck_name, card["name"])
                    if source_sig not in seen_sources[key]:
                        seen_sources[key].add(source_sig)
                        token_map[key]["sources"].append({
                            "set": set_code,
                            "set_name": set_name,
                            "deck": deck_name,
                            "card": card["name"],
                        })
                        total_source_refs += 1

    # Sort tokens alphabetically by name, then type_line
    tokens_sorted = sorted(
        token_map.values(),
        key=lambda t: (t["name"].lower(), t.get("type_line", "").lower())
    )

    # Sort sources within each token: by set order, then deck, then card
    set_order = {s: i for i, s in enumerate(SETS)}
    for token in tokens_sorted:
        token["sources"].sort(key=lambda s: (
            set_order.get(s["set"], 99),
            s["deck"],
            s["card"],
        ))

    output = {
        "metadata": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "total_tokens": len(tokens_sorted),
            "total_source_refs": total_source_refs,
            "decks_scanned": total_decks,
            "sets": SETS,
            "scope": (
                "Official tokens only — entries require a Scryfall oracle_id, meaning "
                "WotC has printed a physical token card for them. Tokens created by card "
                "text that have no official printed token card (e.g. Monkey, Banana, "
                "Zeppelin) are tracked separately as 'unofficial_tokens' on the "
                "individual deck JSON files."
            ),
        },
        "tokens": tokens_sorted,
    }

    out_file = BASE_DIR / "jumpstart-token-index.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    size_kb = out_file.stat().st_size / 1024
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"✓ Generated: {out_file.name}", file=sys.stderr)
    print(f"  Unique tokens:    {len(tokens_sorted)}", file=sys.stderr)
    print(f"  Source refs:      {total_source_refs}", file=sys.stderr)
    print(f"  Decks scanned:    {total_decks}", file=sys.stderr)
    print(f"  File size:        {size_kb:.1f} KB", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
