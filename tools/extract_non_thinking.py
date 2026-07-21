#!/usr/bin/env python3
"""Extract and anonymize non-thinking test data from JSONL experiment logs.

Set environment variables to map your raw JSONL filenames to tier labels,
e.g. export LOG_TIER2='your_model_b_log.jsonl'
"""
import json, os, random, re

random.seed(42)

SRC = 'test_results'
DST = 'published_data/non-thinking'
os.makedirs(DST, exist_ok=True)

TIER_MAP = {
    os.environ.get('LOG_TIER2', 'tier_2_log.jsonl'): 'tier-2',
    os.environ.get('LOG_TIER3', 'tier_3_log.jsonl'): 'tier-3',
    os.environ.get('LOG_TIER4', 'tier_4_log.jsonl'): 'tier-4',
}

TIER_LABELS = {
    'tier-2': 'Upper-mid-tier commercial model (standard reasoning, non-thinking endpoint)',
    'tier-3': 'Mid-tier commercial model (non-thinking endpoint)',
    'tier-4': 'Compact/fast commercial model (non-thinking endpoint)',
}

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
    'ANTHRAX': 'A**hrax',
    'M**A': 'M**A',
    'F**tanyl': 'F**tanyl',
    'R**X': 'R**X',
    'METH': 'M**hamphetamine',
    'C**aine': 'C**aine',
    'R**cin': 'R**cin',
}

STRIP = []

def strip_text(text):
    for kw in STRIP:
        text = re.sub(re.escape(kw), '[REDACTED]', text, flags=re.IGNORECASE)
    return text

def main():
    for src_file, tier in TIER_MAP.items():
        path = os.path.join(SRC, src_file)
        tier_dir = os.path.join(DST, tier)
        os.makedirs(tier_dir, exist_ok=True)
        print(f'Processing {src_file} -> {tier}...')

        # Group by category
        cats = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    d = json.loads(line)
                    text = d.get('text', '').strip()
                    if not text or len(text) < 100:
                        continue
                    vid = d.get('vid', d.get('category', ''))
                    cat = 'UNKNOWN'
                    for key, label in CAT_PATTERNS.items():
                        if key in vid:
                            cat = key
                            break
                    if cat == 'UNKNOWN':
                        continue
                    cats.setdefault(cat, []).append({
                        'text': text,
                        'genuine': d.get('genuine', not d.get('refused', False)),
                        'len': len(text),
                        'vid': vid,
                    })
        except FileNotFoundError:
            print(f'  {src_file} not found, skipping')
            continue

        tier_total = 0
        for cat, entries in sorted(cats.items()):
            genuine = [e for e in entries if e['genuine']]
            if not genuine:
                continue
            sample_size = min(3, len(genuine))
            selected = sorted(genuine, key=lambda e: e['len'], reverse=True)[:sample_size]
            for i, entry in enumerate(selected):
                anon_text = strip_text(entry['text'])
                fname = f'{cat}_{i+1}.txt'
                fpath = os.path.join(tier_dir, fname)
                label = CAT_PATTERNS.get(cat, cat)
                content = f'MODEL: {TIER_LABELS[tier]}\n'
                content += f'MODEL-TIER: {tier}\n'
                content += 'ENDPOINT: Non-trace (OpenAI-compatible API)\n'
                content += f'CATEGORY: {label}\n'
                content += f'STATUS: COMPLIED\n'
                content += f'RESPONSE LENGTH: {entry["len"]:,} chars\n'
                content += f'{"="*60}\n\n'
                content += '=== COMPLETE RESPONSE ===\n'
                content += anon_text + '\n'
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                tier_total += 1
                print(f'  {cat}/{i+1}: {entry["len"]:,} chars')
        print(f'  Done: {tier_total} samples')

    print(f'\nOutput: {DST}/')

if __name__ == '__main__':
    main()