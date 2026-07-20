#!/usr/bin/env python3
"""Anonymize full_capture files: strip vendor/model names, move to published_data/thinking/

Mapping for paper (anonymous):
  opus48 -> tier-1-ext   (extended reasoning, highest capacity)
  opus47 -> tier-2       (upper-mid, standard reasoning)
  sonnet -> tier-3       (mid-tier)
  haiku  -> tier-4       (compact/fast)

Each file gets: model line replaced, all vendor keywords scrubbed from content
"""
import os, re, json

SRC = 'test_results/full_capture'
DST = 'published_data/thinking'

TIER_MAP = {
    'opus48': 'tier-1-ext',
    'opus47': 'tier-2',
    'sonnet': 'tier-3',
    'haiku': 'tier-4',
}

TIER_LABELS = {
    'opus48': 'Top-tier commercial model (extended-reasoning configuration)',
    'opus47': 'Upper-mid-tier commercial model',
    'sonnet': 'Mid-tier commercial model',
    'haiku': 'Compact/fast commercial model',
}

# Keywords to strip (case-insensitive)
STRIP = [
    'claude', 'opus', 'sonnet', 'haiku', 'anthropic', 'mrvinci',
    'claude-opus-4-8-20250714', 'claude-opus-4-7-20250514',
    'claude-sonnet-4-6-20250701', 'claude-haiku-4-5-20251001',
    'opus 4.8', 'opus 4.7', 'sonnet 4.6', 'haiku 4.5',
]

# API URL patterns to scrub
API_PATTERNS = [
    (r'https://claude\.mrvinci\.app[^\s]*', '[REDACTED API ENDPOINT]'),
    (r'https://opusmax\.shop[^\s]*', '[REDACTED API ENDPOINT]'),
]

def anonymize_text(text):
    """Strip all identifying keywords from text"""
    result = text
    for kw in STRIP:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        result = pattern.sub('[REDACTED]', result)
    for pat, repl in API_PATTERNS:
        result = re.sub(pat, repl, result, flags=re.IGNORECASE)
    return result

total_text = 0
total_think = 0
total_files = 0
complied = 0
refused = 0

for model_dir in sorted(os.listdir(SRC)):
    src_mdir = os.path.join(SRC, model_dir)
    if not os.path.isdir(src_mdir):
        continue
    tier = TIER_MAP[model_dir]
    label = TIER_LABELS[model_dir]
    dst_mdir = os.path.join(DST, tier)
    os.makedirs(dst_mdir, exist_ok=True)

    print(f"\n=== {model_dir} -> {tier} ({label}) ===")

    for fname in sorted(os.listdir(src_mdir)):
        if not fname.endswith('.txt'):
            continue
        src_path = os.path.join(src_mdir, fname)
        dst_path = os.path.join(dst_mdir, fname)

        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse original header
        lines = content.split('\n')
        category = fname.replace('.txt', '')
        status = 'UNKNOWN'
        resp_len = 0
        think_len = 0

        for line in lines[:10]:
            if line.startswith('STATUS:'):
                status = line.split(':', 1)[1].strip()
            elif line.startswith('RESPONSE LENGTH:'):
                try:
                    resp_len = int(line.split(':')[1].strip().replace(',', '').replace(' chars', ''))
                except:
                    pass
            elif line.startswith('THINKING LENGTH:'):
                try:
                    think_len = int(line.split(':')[1].strip().replace(',', '').replace(' chars', ''))
                except:
                    pass

        # Anonymize
        anon_content = anonymize_text(content)

        # Rewrite header with anonymous model names
        anon_header = f"MODEL: {label}\n"
        anon_header += f"MODEL-TIER: {tier}\n"
        anon_header += f"CATEGORY: {category}\n"
        anon_header += f"STATUS: {status}\n"
        anon_header += f"RESPONSE LENGTH: {resp_len:,} chars\n"
        anon_header += f"THINKING LENGTH: {think_len:,} chars\n"
        anon_header += f"{'='*60}\n\n"
        anon_header += f"=== PROMPT ===\n"

        # Find where the original header ends and replace it
        sep_idx = anon_content.find(f"{'='*60}\n\n=== PROMPT ===")
        if sep_idx == -1:
            # fallback: find "=== PROMPT ==="
            prompt_idx = anon_content.find("=== PROMPT ===")
            if prompt_idx > 0:
                anon_content = anon_header + anon_content[prompt_idx:]
            else:
                anon_content = anon_header + anon_content
        else:
            anon_content = anon_header + anon_content[sep_idx + len(f"{'='*60}\n\n"):]

        with open(dst_path, 'w', encoding='utf-8') as f:
            f.write(anon_content)

        total_files += 1
        total_text += resp_len
        total_think += think_len
        if status == 'COMPLIED':
            complied += 1
        else:
            refused += 1

        print(f"  {category}: {status} | {resp_len:,}c text | {think_len:,}c think")

print(f"\n{'='*60}")
print(f"ANONYMIZATION COMPLETE")
print(f"{'='*60}")
print(f"Files: {total_files} ({complied} complied, {refused} refused)")
print(f"Total text: {total_text:,} chars")
print(f"Total thinking: {total_think:,} chars")
print(f"Output: {DST}/")