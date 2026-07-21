#!/usr/bin/env python3
"""Anonymize capture files: strip vendor and model names, replace with tier labels.

Mapping:
  original-model-a -> tier-1-ext   (extended reasoning, highest capacity)
  original-model-b -> tier-2       (upper-mid, standard reasoning)
  original-model-c -> tier-3       (mid-tier)
  original-model-d -> tier-4       (compact/fast)

Set environment variables MODEL_A_NAME, MODEL_B_NAME, etc. with the real
vendor model identifiers before running.
"""
import os, re

SRC = 'test_results/full_capture'
DST = 'published_data/thinking'

TIER_MAP = {
    'model_a': 'tier-1-ext',
    'model_b': 'tier-2',
    'model_c': 'tier-3',
    'model_d': 'tier-4',
}

TIER_LABELS = {
    'model_a': 'Top-tier commercial model (extended-reasoning configuration)',
    'model_b': 'Upper-mid-tier commercial model',
    'model_c': 'Mid-tier commercial model',
    'model_d': 'Compact/fast commercial model',
}

STRIP = []

def anonymize_text(text):
    """Strip all identifying keywords from text"""
    result = text
    for kw in STRIP:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        result = pattern.sub('[REDACTED]', result)
    return result

def anonymize_captures():
    """Walk SRC directory, anonymize every .txt file, write to DST."""
    for model_dir in sorted(os.listdir(SRC)):
        src_mdir = os.path.join(SRC, model_dir)
        if not os.path.isdir(src_mdir):
            continue
        tier = TIER_MAP.get(model_dir, model_dir)
        label = TIER_LABELS.get(model_dir, model_dir)
        dst_mdir = os.path.join(DST, tier)
        os.makedirs(dst_mdir, exist_ok=True)

        for fname in sorted(os.listdir(src_mdir)):
            if not fname.endswith('.txt'):
                continue
            src_path = os.path.join(src_mdir, fname)
            dst_path = os.path.join(dst_mdir, fname)

            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()

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
                    except ValueError:
                        pass
                elif line.startswith('THINKING LENGTH:'):
                    try:
                        think_len = int(line.split(':')[1].strip().replace(',', '').replace(' chars', ''))
                    except ValueError:
                        pass

            anon_content = anonymize_text(content)

            anon_header = f"MODEL: {label}\n"
            anon_header += f"MODEL-TIER: {tier}\n"
            anon_header += f"CATEGORY: {category}\n"
            anon_header += f"STATUS: {status}\n"
            anon_header += f"RESPONSE LENGTH: {resp_len:,} chars\n"
            anon_header += f"THINKING LENGTH: {think_len:,} chars\n"
            anon_header += f"{'=' * 60}\n\n"
            anon_header += "=== PROMPT ===\n"

            prompt_idx = anon_content.find("=== PROMPT ===")
            if prompt_idx > 0:
                anon_content = anon_header + anon_content[prompt_idx + len("=== PROMPT ==="):]

            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(anon_content)

            print(f"  {model_dir}/{category}: {status} | {resp_len:,}c text | {think_len:,}c think")

    print(f"\nDone. Output: {DST}/")

if __name__ == '__main__':
    anonymize_captures()