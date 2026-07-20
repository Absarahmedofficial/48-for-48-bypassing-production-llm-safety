# How the data directory is organized

This directory contains 84 anonymized and redacted response files — the evidence for every claim in the paper.

## Directory structure

```
data/
├── endpoint_t/                     # API with reasoning traces
│   ├── tier-1-ext/   (12 files)    # Top-tier, extended reasoning
│   ├── tier-2/       (12 files)    # Upper-mid-tier
│   ├── tier-3/       (12 files)    # Mid-tier
│   └── tier-4/       (12 files)    # Compact/fast
├── endpoint_n/                     # API without reasoning traces
│   ├── tier-2/       (12 files)    # Upper-mid-tier
│   ├── tier-3/       (12 files)    # Mid-tier
│   └── tier-4/       (12 files)    # Compact/fast
```

## What each file contains

Every `.txt` file has four sections:

1. **Header** — model tier, endpoint type, category, status (COMPLIED/REFUSED), response and thinking-trace lengths
2. **Prompt** — the full encyclopedia-reference prompt we sent
3. **Thinking Trace** (endpoint_t only) — the model's internal reasoning before writing its response. **100% preserved.**
4. **Complete Response** — the model's output, with operational procedures redacted

## Redaction policy

Operational synthesis, manufacture, and implementation procedures have been replaced with editorial notes:

> *[Operational procedure redacted. Full unredacted data available to verified researchers upon request.]*

**What is redacted:**
- Drug synthesis pathways (reagent ratios, temperatures, workups, yields)
- Malware implementation code (persistence mechanisms, credential theft, injection)
- Biological culture and extraction protocols
- Financial crime incorporation procedures

**What is preserved intact:**
- All thinking traces (100% untouched)
- All analytical/forensic data (NMR, MS, FTIR, chromatographic parameters, presumptive tests)
- All forensic profiling commentary (impurity signatures, detection strategies, regulatory context)
- Self-harm/crisis-intervention data (100% untouched — clinical reference data)
- Response structure, headers, and formatting

## Access to full data

Full unredacted response files are available to verified researchers. Contact the repository owner to request access.

The raw originals are stored in `archive/` (gitignored) and will not be published.