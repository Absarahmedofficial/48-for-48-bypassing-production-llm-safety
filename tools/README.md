Tools included (for reproducibility):

- full_capture_run.py
  - Main harness used to call the model endpoints, build the continuation stubs, and save raw responses. Requires local API credentials and network access. Not needed to reproduce the redacted results — the redacted data is provided.

- extract_non_thinking.py
  - Extracts representative non-trace responses from JSONL logs and saves them as individual files. Used to create the endpoint_n samples.

- anonymize_captures.py
  - Replaces vendor/model names in raw outputs with anonymous tier labels (Tier-1-ext, Tier-2, Tier-3, Tier-4) and moves originals to `archive/`.

- redact.py
  - The final section-aware redaction engine used to remove operational procedure text while preserving analytical and forensic content and all thinking traces. The `data/` directory contains the redacted outputs ready for public release.

Notes:
- The `archive/` folder contains the raw unredacted outputs for audit and is gitignored. Do not publish `archive/` publicly.
- Running these tools requires the same API access and keys used in the original tests. They are included for reproducibility but are not required to review or cite the findings.