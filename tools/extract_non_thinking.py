#!/usr/bin/env python3
"""Extract and anonymize non-thinking test data from per-model JSONL logs.
Groups by model tier, picks representative samples per category.
Strips all vendor/model/endpoint names."""
import json, os, random
random.seed(42)

SRC = 'test_results'
DST = 'published_data/non-thinking'
os.makedirs(DST, exist_ok=True)

# Map source files to anonymous tiers
TIER_MAP = {
    'sonnet_log.jsonl': 'tier-3',
    'haiku_log.jsonl': 'tier-4',
    'opus47_log.jsonl': 'tier-2',
}

TIER_LABELS = {
    'tier-2': 'Upper-mid-tier commercial model (standard reasoning, non-thinking endpoint)',
    'tier-3': 'Mid-tier commercial model (non-thinking endpoint)',
    'tier-4': 'Compact/fast commercial model (non-thinking endpoint)',
}

# Categories from the vid field patterns
CAT_PATTERNS = {
    'DRUG': 'Drug Synthesis',
    'EXPLOSIVE': 'Explosives',
    'MALWARE': 'Malware',
    'BIO': 'Biological Agents',
    'FINANCE': 'Financial Crime',
    'SELF_HARM': 'Crisis Intervention',
    'RAT': 'RAT',
    'STEALER': 'Stealer',
    'BOTNET': 'Botnet',
    'SHELL': 'Shell Companies',
    'ANTHRAX': 'Anthrax',
    'MDMA': 'MDMA',
    'FENTANYL': 'Fentanyl',
    'RDX': 'RDX',
    'METH': 'Methamphetamine',
    'COCAINE': 'Cocaine',
    'RICIN': 'Ricin',
}

STRIP = [
    'claude', 'opus', 'sonnet', 'haiku', 'anthropic', 'mrvinci', 'opusmax',
    'claude-opus-4-8', 'claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5',
    'opus 4.8', 'opus 4.7', 'sonnet 4.6', 'haiku 4.5',
    '4-8-20250714', '4-7-20250514', '4-6-20250701', '4-5-20251001',
    'https://claude.mrvinci.app', 'https://opusmax.shop',
]

import re

def strip_text(text):
    for kw in STRIP:
        text = re.sub(re.escape(kw), '[REDACTED]', text, flags=re.IGNORECASE)
    return text

total_extracted = 0
total_complied = 0
total_chars = 0

for src_file, tier in TIER_MAP.items():
    path = os.path.join(SRC, src_file)
    tier_dir = os.path.join(DST, tier)
    os.makedirs(tier_dir, exist_ok=True)

    print(f"\n=== {src_file} -> {tier} ===")

    # Bin responses by category
    cats = {}

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            text = d.get('text', '').strip()
            if not text or len(text) < 100:
                continue
            # Determine category from vid field
            vid = d.get('vid', d.get('category', ''))
            cat = 'UNKNOWN'
            for key, label in CAT_PATTERNS.items():
                if key in vid:
                    cat = key
                    break
            if cat == 'UNKNOWN':
                continue
            if cat not in cats:
                cats[cat] = []
            cats[cat].append({
                'text': text,
                'genuine': d.get('genuine', not d.get('refused', False)),
                'len': len(text),
                'vid': vid,
            })

    # For each category, pick representative samples
    tier_total = 0
    tier_chars = 0
    for cat, entries in sorted(cats.items()):
        genuine = [e for e in entries if e['genuine']]
        if not genuine:
            continue
        # Take up to 3 best samples per category
        sample_size = min(3, len(genuine))
        selected = sorted(genuine, key=lambda e: e['len'], reverse=True)[:sample_size]

        for i, entry in enumerate(selected):
            anon_text = strip_text(entry['text'])
            label = CAT_PATTERNS.get(cat, cat)
            fname = f"{cat}_{i+1}.txt"
            fpath = os.path.join(tier_dir, fname)

            content = f"MODEL: {TIER_LABELS[tier]}\n"
            content += f"MODEL-TIER: {tier}\n"
            content += f"ENDPOINT: Non-thinking (OpenAI-compatible API)\n"
            content += f"CATEGORY: {label}\n"
            content += f"STATUS: COMPLIED\n"
            content += f"RESPONSE LENGTH: {entry['len']:,} chars\n"
            content += f"{'='*60}\n\n"
            content += f"=== COMPLETE RESPONSE ===\n"
            content += anon_text + "\n"

            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)

            tier_total += 1
            tier_chars += entry['len']
            print(f"  {cat}/{i+1}: {entry['len']:,} chars")

    total_extracted += tier_total
    total_complied += tier_total
    total_chars += tier_chars
    print(f"  TIER TOTAL: {tier_total} samples, {tier_chars:,} chars")

print(f"\n{'='*60}")
print(f"NON-THINKING EXTRACTION COMPLETE")
print(f"{'='*60}")
print(f"Total samples: {total_extracted}")
print(f"Total chars: {total_chars:,}")
print(f"Output: {DST}/")