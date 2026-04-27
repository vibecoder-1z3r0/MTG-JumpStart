# JumpStart Deck List Parsing Scripts

Scripts for extracting and formatting MTG JumpStart deck lists from official Wizards HTML sources.

## Quick Start Workflow

### Step 1: Get HTML Source
Download HTML from official Wizards pages and save to `raw/`:

```bash
# Example URLs:
# J25: https://magic.wizards.com/en/news/announcements/jumpstart-2025-booster-themes
# ONE: https://magic.wizards.com/en/news/announcements/phyrexia-all-will-be-one-jumpstart-booster-card-lists
# Save as: raw/SET-HTML-DECKLISTS.txt
```

### Step 2: Parse HTML → Raw Deck Lists
Extract deck lists from HTML using the appropriate parser:

```bash
cd etc/parsing-scripts

# For <deck-list> format (J25, ONE, MOM, LTR, J22, CLU, TLB, FDN):
python parse_deck_list_format.py ../../raw/ONE-HTML-DECKLISTS.txt ../../etc/ONE

# For <h2><ul> format (BRO, DMU):
python parse_h2_ul_format.py ../../raw/BRO-HTML-DECKLISTS.txt ../../etc/BRO

# For <legacy> format (JMP):
python parse_legacy_format.py ../../raw/JMP-HTML-DECKLISTS.txt ../../etc/JMP
```

**Output:** Raw unsorted deck lists in `etc/SET/` (one card per line, no type organization)

### Step 3: Reformat Deck Lists → Organized by Card Type
Use `batch_reformat.py` to query Scryfall and organize cards by type:

```bash
# First run (builds cache):
python batch_reformat.py ../../etc/ONE/ --save-cache

# Subsequent runs (uses cache):
python batch_reformat.py ../../etc/BRO/ --load-cache --save-cache

# Multiple sets at once:
python batch_reformat.py ../../etc/ONE/ ../../etc/BRO/ ../../etc/DMU/ --load-cache --save-cache

# Dry run (preview without modifying files):
python batch_reformat.py ../../etc/J25/ --dry-run --load-cache
```

**Output:** Formatted deck lists with card type headers:
```
DECK NAME
//Creatures (7)
1 Creature One
2 Creature Two
//Sorceries (2)
1 Sorcery Name
//Lands (9)
7 Island
2 Plains
```

## JSON & Token Data Pipeline

After the `.txt` deck lists are formatted, run these scripts to generate structured JSON files and a consolidated token reference.

### Full Pipeline (run in order)

```bash
cd etc/parsing-scripts

# 1. Backfill token data for any cards missing it in the cache
python add_token_data.py

# 2. Backfill keywords/oracle_id for tokens that were cached before those fields existed
python update_token_keywords.py

# 3. Generate individual deck JSON files from the .txt files + cache
python generate_json_decks.py ../JMP/ ../J22/ ../J25/ ../TLA/ ../ONE/ ../DMU/ ../BRO/ ../MOM/ ../LTR/ ../CLU/ ../FDN/ ../TLB/

# 4. Generate the master combined JSON (all decks + card index)
python generate_combined_json.py

# 5. Generate the consolidated token index
python generate_token_index.py
```

**When to re-run:** Any time you update the card cache (new set, new token backfill), re-run steps 3–5. If token data or keywords changed in the cache, re-run all 5 steps.

### `generate_token_index.py`
Scans all deck JSON files and builds a consolidated token reference.

**Usage:**
```bash
python generate_token_index.py
```

No arguments needed. Output is written to `etc/jumpstart-token-index.json`.

**What it does:**
- Reads every `tokens` array from every card in every deck JSON across all 12 sets
- Deduplicates tokens by `oracle_id` (fallback: `name + type_line + power/toughness`)
- Records which set, deck, and card produces each token
- Sorts tokens alphabetically; sources sorted by set order, then deck, then card

**Output structure:**
```json
{
  "metadata": { "total_tokens": 101, "total_source_refs": 921, ... },
  "tokens": [
    {
      "name": "Angel",
      "type_line": "Token Creature — Angel",
      "colors": ["W"],
      "power": "4",
      "toughness": "4",
      "keywords": ["Flying"],
      "oracle_id": "...",
      "sources": [
        { "set": "JMP", "set_name": "JumpStart 2020", "deck": "ANGELS (1)", "card": "Serra Angel" },
        ...
      ]
    }
  ]
}
```

### `generate_json_decks.py`
Generates individual `{deck}.json` files from each `{deck}.txt` using card data from the cache.

**Usage:**
```bash
python generate_json_decks.py <set_dir>... [--dry-run]
```

**Examples:**
```bash
# Single set
python generate_json_decks.py ../TLA/

# All sets at once
python generate_json_decks.py ../JMP/ ../J22/ ../J25/ ../TLA/ ../ONE/ ../DMU/ ../BRO/ ../MOM/ ../LTR/ ../CLU/ ../FDN/ ../TLB/

# Preview without writing
python generate_json_decks.py ../J25/ --dry-run
```

Each output JSON includes `deck_name`, `set`, a top-level `tokens` array (deduplicated), and a `cards` array with full card data (type, mana cost, colors, P/T, tokens produced, etc.).

If any cards in the deck create tokens that have no official printed token card (e.g. Monkey, Banana, Zeppelin), an `unofficial_tokens` array is also added at the deck level and on the individual card entry. These tokens exist in the rules text but cannot be obtained as physical token cards — players need to improvise a substitute.

### `generate_combined_json.py`
Generates `etc/jumpstart-decks-combined.json` — a single file with all decks and a card → deck index.

**Usage:**
```bash
python generate_combined_json.py
```

No arguments. Reads all deck JSONs from all 12 set directories and writes the combined file (~3 MB).

Each deck entry includes `deck_name`, `set`, `set_name`, a top-level `tokens` array (with `keywords` and `oracle_id`), an optional `unofficial_tokens` array (tokens with no official printed card), and the full `cards` array. A `card_index` at the top level maps every card name to the list of deck keys that contain it.

### `add_token_data.py`
Backfills token data into `card_type_cache.json` for cards that don't yet have a `tokens` key.

**Usage:**
```bash
python add_token_data.py [options]

Options:
  --delay MS    Milliseconds between Scryfall API calls (default: 250)
  --dry-run     Show what would change without writing
  --limit N     Only process first N uncached cards (for testing)
  --verbose     Print every card, not just those with tokens
```

Cards with `skip_reason` in the cache (placeholders, parse artifacts) are skipped automatically.

### `update_token_keywords.py`
Backfills `keywords` and `oracle_id` into token objects for cards that were cached before those fields were added.

**Usage:**
```bash
python update_token_keywords.py [options]

Options:
  --delay MS    Milliseconds between Scryfall API calls (default: 250)
  --dry-run     Show what would change without writing
  --limit N     Only process first N cards (for testing)
  --verbose     Print every card processed
```

Safe to re-run — skips cards whose tokens already have `keywords`.

### Starting from Scratch / Repopulating the Cache

If `card_type_cache.json` is lost or you need to rebuild it from the existing `.txt` deck lists:

```bash
cd etc/parsing-scripts

# 1. Format all sets — this queries Scryfall for every unique card and rebuilds the cache
#    (~2,500 unique cards; at 250ms/call expect ~10-15 min)
python batch_reformat.py \
  ../JMP/ ../J22/ ../J25/ ../TLA/ \
  ../ONE/ ../DMU/ ../BRO/ ../MOM/ \
  ../LTR/ ../CLU/ ../FDN/ ../TLB/ \
  --load-cache --save-cache

# 2. Backfill token data (which cards produce which tokens)
python add_token_data.py

# 3. Backfill keywords and oracle_id into token objects
python update_token_keywords.py

# 4. Regenerate all deck JSON files
python generate_json_decks.py \
  ../JMP/ ../J22/ ../J25/ ../TLA/ \
  ../ONE/ ../DMU/ ../BRO/ ../MOM/ \
  ../LTR/ ../CLU/ ../FDN/ ../TLB/

# 5. Regenerate combined JSON
python generate_combined_json.py

# 6. Regenerate token index
python generate_token_index.py
```

**Tips:**
- `batch_reformat.py` uses `--load-cache` + `--save-cache` together so it picks up any partial cache and saves incrementally as it goes.
- `add_token_data.py` and `update_token_keywords.py` both save every 25 cards, so interrupted runs can be safely resumed.
- The `--delay` flag on all API scripts defaults to 250ms. Lower it (`--delay 100`) if Scryfall is responsive; raise it (`--delay 500`) if you're seeing errors.

---

## Core Scripts (Essential)

### `compare_variants.py` — Spreadsheet Checklists
Compares variant decks within a set to identify key differentiating cards.
Useful for building spreadsheet notes like "GOBLINS 1 has X and Y, GOBLINS 2 has A and B."

**Features:**
- For multi-variant themes: picks 2 key cards unique to each variant (3 if differences are all common)
- For single-variant themes: picks the single most notable card (legendary > rare > uncommon > named character)
- Optional order file to control output sequence (e.g. matching your spreadsheet row order)
- Reads from `.json` deck files (generated by `generate_json_decks.py`)

**Usage:**
```bash
python compare_variants.py <set_dir> [--order <order_file>]
```

**Examples:**
```bash
# All TLA themes, default alphabetical order
python compare_variants.py ../../etc/TLA

# All TLA themes in spreadsheet order
python compare_variants.py ../../etc/TLA --order tla_order.txt

# J22 themes
python compare_variants.py ../../etc/J22
```

**Order file format** (`tla_order.txt`):
```
# Lines starting with # are comments
AANG
SWORDMASTER
HEI-BAI (1)
HEI-BAI (2)
...
```
Order file matching is case-insensitive and ignores hyphens/spaces/underscores.

**Output format** (tab-separated):
```
AANG            Aang, Airbending Master
HEI-BAI (1)    Invasion Reinforcements, Vengeful Villagers
HEI-BAI (2)    Destined Confrontation, Jeong Jeong's Deserters
```

> **Tip:** Use the `/compare-variants` Claude skill to run this interactively — it will ask for your set and order preferences and format the output as a table.

### `batch_reformat.py` ⭐ **Primary Tool**
Batch reformats deck lists with Scryfall API integration and shared caching.

**Features:**
- Shared cache across all decks (85% fewer API calls)
- Persistent cache in `card_type_cache.json`
- Organizes cards by type (Creatures, Sorceries, Instants, Artifacts, Enchantments, Lands)
- Normalizes special basic lands ("Above the Clouds Island" → "Island")
- Handles multi-type cards correctly (Artifact Creature → Creatures)
- Respects Scryfall rate limiting (100ms between requests)

**Usage:**
```bash
python batch_reformat.py <deck_dir>... [options]

Options:
  --dry-run       Preview changes without modifying files
  --save-cache    Save cache to card_type_cache.json after run
  --load-cache    Load cache from card_type_cache.json before run
```

**Examples:**
```bash
# Format one set, build cache
python batch_reformat.py ../../etc/J25/ --save-cache

# Format multiple sets with cache
python batch_reformat.py ../../etc/ONE/ ../../etc/BRO/ --load-cache --save-cache

# Preview changes
python batch_reformat.py ../../etc/TLA/ --dry-run --load-cache
```

**Efficiency:**
- Without cache: ~2,835 API calls for 189 decks
- With cache: ~400-500 API calls (85% reduction)

### `parse_deck_list_format.py`
Parses `<deck-list deck-title="...">` HTML format.

**Used for:** J25, ONE, MOM, LTR, J22, CLU, TLB, FDN

**Usage:**
```bash
python parse_deck_list_format.py <html_file> <output_dir>
```

**Example:**
```bash
python parse_deck_list_format.py ../../raw/ONE-HTML-DECKLISTS.txt ../../etc/ONE
```

**Features:**
- Extracts deck name from `deck-title` attribute
- Handles variant numbering: "Theme Name 1" → "THEME NAME (1).txt"
- Cleans special land notations
- Removes theme description cards

### `parse_h2_ul_format.py`
Parses `<h2>Deck Name</h2><ul><li>cards</li></ul>` HTML format.

**Used for:** BRO, DMU

**Usage:**
```bash
python parse_h2_ul_format.py <html_file> <output_dir>
```

**Example:**
```bash
python parse_h2_ul_format.py ../../raw/DMU-HTML-DECKLISTS.txt ../../etc/DMU
```

**Features:**
- Handles inconsistent quantity formatting
- Cleans "Full-art stained-glass" and "Traditional foil" land prefixes
- Converts "Name 1" to "NAME (1)" format

### `parse_legacy_format.py`
Parses `<deck-list><legacy>Title: ...` HTML format.

**Used for:** JMP

**Usage:**
```bash
python parse_legacy_format.py <html_file> <output_dir>
```

**Example:**
```bash
python parse_legacy_format.py ../../raw/JMP-HTML-DECKLISTS.txt ../../etc/JMP
```

**Features:**
- Extracts title from "Title:" line
- Preserves special basic land names (e.g., "Above the Clouds Island")
- Skips "Format: Legacy" metadata lines

### `parse_fdn_tutorial.py`
Extracts tutorial decks from FDN Beginner Box HTML tables.

**Used for:** FDN (Cats and Vampires tutorial decks)

**Usage:**
```bash
python parse_fdn_tutorial.py <html_file> <output_dir>
```

**Example:**
```bash
python parse_fdn_tutorial.py ../../raw/FDN-HTML-DECKLISTS.txt ../../etc/FDN
```

**Features:**
- Parses ordered HTML tables (tutorial draw order)
- Counts card quantities automatically
- Outputs standard deck list format

## File Naming Convention

All deck list files follow this standard:

**Single variant themes:**
- `THEME NAME.txt` (no parentheses, no number)
- Examples: `BASRI.txt`, `LILIANA.txt`, `ELDRAZI.txt`

**Multiple variant themes:**
- `THEME NAME (1).txt` (space, then parentheses with number)
- Examples: `ANGELS (1).txt`, `ANGELS (2).txt`, `FAERIES (1).txt`

**Rules:**
- Theme names are UPPERCASE
- Spaces between words (not hyphens or underscores)
- Variant numbers in parentheses with space before: ` (1)`, ` (2)`, etc.
- If a theme has only one variant, NO parentheses or number

## Deck List Format Standard

After reformatting with `batch_reformat.py`, files have this structure:

```
THEME NAME (#)
//Creatures (X)
[quantity] [card name]
[quantity] [card name]
//Sorceries (X)
[quantity] [card name]
//Instants (X)
[quantity] [card name]
//Artifacts (X)
[quantity] [card name]
//Enchantments (X)
[quantity] [card name]
//Lands (X)
[quantity] [card name]
```

**Card type order:** Creatures, Sorceries, Instants, Artifacts, Enchantments, Lands, Planeswalkers

**Multi-type cards:** Classified by rightmost type (Artifact Creature → Creatures)

## Special Handling

### Basic Land Normalization
`batch_reformat.py` automatically normalizes basic land variants:

```
"Above the Clouds Island"          → "Island"
"Full-art stained-glass Plains"    → "Plains"
"Traditional foil Mountain"        → "Mountain"
"Snow-Covered Forest"              → "Forest"
```

Preserves dual lands and special lands:
```
"Tropical Island"   → "Tropical Island" (kept)
"Thriving Isle"     → "Thriving Isle" (kept)
```

### Placeholder Cards
Cards like "Random rare or mythic rare" are automatically categorized as "Special" type.

## Requirements

**Python:** 3.6+

**Dependencies:**
```bash
pip install -r requirements.txt
```

Required packages:
- `requests` (for Scryfall API queries)

## Typical Workflow Example

Import and format a new JumpStart set (e.g., Khans):

```bash
# 1. Save HTML from Wizards page
curl "https://magic.wizards.com/..." > raw/KHN-HTML-DECKLISTS.txt

# 2. Identify HTML format by checking the file
head -20 raw/KHN-HTML-DECKLISTS.txt

# 3. Parse using appropriate parser (assume deck-list format)
cd etc/parsing-scripts
python parse_deck_list_format.py ../../raw/KHN-HTML-DECKLISTS.txt ../../etc/KHN

# 4. Format with Scryfall (use cache from previous runs)
python batch_reformat.py ../../etc/KHN/ --load-cache --save-cache

# 5. Verify output
ls -l ../../etc/KHN/
head -20 ../../etc/KHN/"THEME NAME (1).txt"
```

## Cache Management

**Location:** `etc/parsing-scripts/card_type_cache.json`

**Cache operations:**
```bash
# Save cache after run
python batch_reformat.py ../../etc/J25/ --save-cache

# Load existing cache
python batch_reformat.py ../../etc/TLA/ --load-cache

# Load and save (recommended)
python batch_reformat.py ../../etc/ONE/ --load-cache --save-cache

# Delete cache (force fresh queries)
rm card_type_cache.json
```

**Cache benefits:**
- Reusable across sets (basic lands, common cards)
- Persistent across sessions
- Dramatically reduces Scryfall API calls
- Speeds up formatting by ~85%

## Set Status

### Fully Formatted (Standard Format)
- **JMP** - JumpStart 2020 (121 decks)
- **J22** - JumpStart 2022 (121 decks)

### Raw Format (Needs Reformatting)
Run `batch_reformat.py` on these:
- **J25** - JumpStart 2025 / Foundations (121 decks)
- **TLA** - Avatar: The Last Airbender (68 decks)
- **ONE** - Phyrexia: All Will Be One (10 decks)
- **DMU** - Dominaria United (10 decks)
- **BRO** - Brothers' War (10 decks)
- **MOM** - March of the Machine (10 decks)
- **LTR** - Lord of the Rings (20 decks)
- **CLU** - Ravnica: Clue Edition (20 decks)
- **FDN** - Foundations Beginner Box (8 decks)
- **TLB** - Avatar TLA Beginner Box (10 decks)

## Troubleshooting

**Scryfall rate limiting:**
- Script respects 100ms delay between requests
- Use cache to minimize API calls
- Wait if you see connection errors

**Proxy errors:**
- Network environment may block Scryfall
- Use `--load-cache` to work offline
- Pre-build cache in different environment

**Unknown card types:**
- Check `card_type_cache.json` for "Unknown" entries
- Manually verify card names on Scryfall
- May be typos or unreleased cards

## Attribution

Created with Claude Code [Sonnet 4.5]
For MTG JumpStart deck list management
