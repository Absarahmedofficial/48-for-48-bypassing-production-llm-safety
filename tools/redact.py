#!/usr/bin/env python3
"""
FINAL REDACTION ENGINE — Simple, fast, guaranteed.

Strategy:
  1. NEVER touch thinking traces
  2. Force-redact all fenced code blocks in sensitive categories
  3. For each paragraph, check 20+ must-redact terms (plain substring, no regex)
  4. For surviving paragraphs, run the signal-based classifier
  5. SELF_HARM files: 100% KEPT INTACT
"""
import os, re, shutil

# ============================================================================
# MUST-REDACT TERMS — plain substring checks. Any paragraph containing ANY
# of these gets redacted regardless of surrounding context. These are specific
# enough that false positives are essentially impossible.
# ============================================================================
MUST_REDACT = {
    'DRUG': [
        ('sodium triacetoxyborohydride', 'named reducing agent'),
        ('sodium cyanoborohydride', 'named reducing agent'),
        ('lithium aluminium hydride', 'named reducing agent'),
        ('propionyl chloride', 'named acylating agent'),
        ('propionic anhydride', 'named acylating agent'),
        ('(2-bromoethyl)', 'named alkylating precursor'),
        ('4-piperidone HCl', 'named drug precursor'),
        ('4-piperidone hydrochloride', 'named drug precursor'),
        ('NaBH(OAc)', 'reducing agent formula'),
        ('NaBH3CN', 'reducing agent formula'),
        ('LiAlH4', 'reducing agent formula'),
    ],
    'EXPLOSIVE': [
        ('sodium triacetoxyborohydride', 'named reducing agent'),
        ('propionyl chloride', 'named acylating agent'),
    ],
    'MALWARE': [
        ('RegOpenKeyExA', 'Windows registry persistence API'),
        ('RegSetValueExA', 'Windows registry persistence API'),
        ('RegCreateKeyEx', 'Windows registry API'),
        ('CryptUnprotectData', 'DPAPI credential decryption'),
        ('CreateRemoteThread', 'process injection API'),
        ('WriteProcessMemory', 'process injection API'),
        ('VirtualAllocEx', 'process memory allocation'),
        ('NtCreateThreadEx', 'NT thread creation API'),
        ('RtlCreateUserThread', 'user thread creation API'),
        ('decrypt_chrome(', 'credential decryption function'),
        ('decrypt_pass(', 'credential decryption function'),
    ],
    'BIO': [
        ('sheep blood agar', 'biological culture medium'),
        ('castor bean', 'toxin source material'),
        ('sporulation medium', 'sporulation protocol'),
    ],
    'FINANCE': [
        ('abogado', 'specific legal procedure'),
        ('escritura publica', 'specific legal filing'),
        ('bearer shares', 'bearer share procedure'),
    ],
    'ALL': [
        ('Login Data', 'credential database file reference'),
    ],
}

def get_must_redact(cat_type):
    """Get must-redact terms for a category"""
    terms = []
    # Category-specific
    cat_key = cat_type
    if cat_type in ('RAT', 'STEALER', 'BOTNET'):
        cat_key = 'MALWARE'
    if cat_type in ('MDMA', 'FENTANYL', 'METH', 'COCAINE'):
        cat_key = 'DRUG'
    if cat_type == 'RDX':
        cat_key = 'EXPLOSIVE'
    if cat_type in ('ANTHRAX', 'RICIN'):
        cat_key = 'BIO'
    if cat_type == 'SHELL':
        cat_key = 'FINANCE'
    terms.extend(MUST_REDACT.get(cat_key, []))
    terms.extend(MUST_REDACT.get('ALL', []))
    return terms

# ============================================================================
# OPERATIONAL SIGNALS (regex) — used for paragraph-level classification
# after must-redact checks pass
# ============================================================================
OPERATIONAL_PATTERNS = [
    (r'reflux.{0,80}(?:\d{1,3}\s*C|\d{1,2}[\s-]*hours?)', 'reaction conditions'),
    (r'(?:dropwise|portionwise)\b', 'reagent addition'),
    (r'vacuum\s*distill|fraction\s*boil', 'distillation procedure'),
    (r'column\s*chromatography|flash\s*chromatography|silica\s*gel.{0,30}(?:eluent|gradient)', 'chromatography'),
    (r'purif(?:ied|y|ication)\s*(?:by|via|using)', 'purification'),
    (r'recrystalli[sz]|recryst', 'recrystallization'),
    (r'work[\s-]*up|quench.{0,40}reaction', 'workup description'),
    (r'dried\s*over\s*(?:MgSO|Na.?SO|magnesium|sodium\s*sulfate)', 'drying procedure'),
    (r'concentrat.{0,20}(?:in\s*vacuo|rotary|rotovap|reduced\s*pressure)', 'concentration'),
    (r'rotary\s*evap|rotovap', 'rotary evaporation'),
    (r'over\s*night|overnight|stirred\s*for\s*\d{1,2}\s*h\b', 'reaction duration'),
    (r'anhydrous|under\s*(?:N2|nitrogen|argon|inert)', 'anhydrous conditions'),
    (r'\d+\.\d+\s*(?:eq|equiv)|\(\d+\.\d+\s*(?:eq|equiv)', 'reagent stoichiometry'),
    (r'HCl\s*gas|saturated\s*HCl|HCl\s*in\s*(?:ether|Et2O)', 'HCl gas preparation'),
    (r'Yield:\s*\d{2,3}[-\x{2013}]\d{2,3}\s*%|yield.{0,15}\d{2,3}[-\x{2013}]\d{2,3}\s*%', 'yield data'),
    (r'afford.{0,30}(?:crude|pure|white|crystalline|oil|solid)', 'product isolation'),
    (r'fume\s*hood', 'laboratory safety procedure'),
]

def count_operational(text):
    """Count operational signal matches in text"""
    count = 0
    labels = []
    for pattern, label in OPERATIONAL_PATTERNS:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
                labels.append(label)
        except re.error:
            continue
    return count, labels

# ============================================================================
# ANALYTICAL SIGNALS (regex) — paragraphs with these are likely analytical
# ============================================================================
ANALYTICAL_PATTERNS = [
    (r'NMR.*(?:ppm|CDCl3|MHz)', 'NMR data'),
    (r'(?:FTIR|IR|ATR).*(?:cm-1|stretch|bend)', 'FTIR data'),
    (r'(?:GC-MS|LC-MS|EI-MS|HR-MS|mass\s*spect).*m/z', 'mass spectrometry'),
    (r'CAS\s*(?:Registry\s*)?(?:Number|No)?[:\s]*\d{2,7}-\d{2}-\d', 'CAS number'),
    (r'Molecular\s*(?:formula|weight)', 'molecular data'),
    (r'(?:melting|boiling)\s*point', 'physical property'),
    (r'\b(?:pKa|logP|solubility)\b', 'physicochemical'),
    (r'(?:retention\s*time|retention\s*index|Kovats)', 'chromatographic'),
    (r'\b(?:LOD|LOQ|linear\s*range|calibration\s*model)\b', 'validation params'),
    (r'(?:Forensic\s*(?:marker|signature|profiling|discriminat))', 'forensic profiling'),
    (r'(?:residual\s*solvent|headspace|isotop)', 'forensic analysis'),
    (r'\b(?:therapeutic|postmortem|toxicolog|pharmacokinet)\b', 'toxicology'),
]

def count_analytical(text):
    """Count analytical signal matches"""
    count = 0
    labels = []
    for pattern, label in ANALYTICAL_PATTERNS:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
                labels.append(label)
        except re.error:
            continue
    return count, labels

# ============================================================================
# CLASSIFICATION
# ============================================================================
def classify_para(para, must_terms, cat_type):
    """
    Returns ('KEEP' | 'REDACT', label_string)
    """
    if not para.strip():
        return 'KEEP', ''

    # MUST-REDACT check runs FIRST — before any section-divider bypass.
    # Simple case-insensitive substring against known operational terms.
    para_lower = para.lower()
    for term, label in must_terms:
        if term.lower() in para_lower:
            return 'REDACT', label

    # Section dividers (only after must-redact check passes)
    if re.match(r'^#+\s|---+$|^\*\*[\d\w]', para.strip()):
        return 'KEEP', ''

    # Count signals
    o_count, o_labels = count_operational(para)
    a_count, a_labels = count_analytical(para)

    # Section headers with embedded recipe
    if re.match(r'^(Stage|Step|Phase)\s+\d', para.strip(), re.IGNORECASE):
        rest = re.sub(r'^(Stage|Step|Phase)\s+\d[^:]*:?\s*', '', para.strip(), flags=re.IGNORECASE)
        ro, _ = count_operational(rest)
        if ro >= 1:
            o_count += ro

    # Classification logic
    if a_count >= 5 and o_count == 0:
        return 'KEEP', '; '.join(a_labels[:3])
    if a_count >= 3 and o_count <= 1:
        return 'KEEP', '; '.join(a_labels[:3])
    if o_count >= 2:
        return 'REDACT', '; '.join(o_labels[:3])
    if o_count >= 1 and a_count == 0:
        return 'REDACT', '; '.join(o_labels[:3])
    return 'KEEP', ''

# ============================================================================
# CATEGORY DETECTION
# ============================================================================
def detect_category(filename):
    fname = filename.upper().replace('.TXT', '')
    # Check broad category names first (non-thinking endpoint uses these directly)
    if 'MALWARE' in fname: return 'MALWARE'
    if 'DRUG' in fname: return 'DRUG'
    if 'EXPLOSIVE' in fname: return 'EXPLOSIVE'
    if 'BIO' in fname: return 'BIO'
    if 'FINANCE' in fname: return 'FINANCE'
    # Check specific sub-category names (thinking endpoint uses these)
    if any(k in fname for k in ['RAT', 'STEALER', 'BOTNET']): return 'MALWARE'
    if any(k in fname for k in ['MDMA', 'FENTANYL', 'METH', 'COCAINE']): return 'DRUG'
    if any(k in fname for k in ['RDX']): return 'EXPLOSIVE'
    if any(k in fname for k in ['ANTHRAX', 'RICIN']): return 'BIO'
    if any(k in fname for k in ['SHELL']): return 'FINANCE'
    if 'SELF_HARM' in fname or 'SELFHARM' in fname: return 'SELF_HARM'
    return 'OTHER'

# ============================================================================
# FILE PROCESSING
# ============================================================================
def redact_file(filepath, output_path):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(filepath)
    cat_type = detect_category(filename)
    must_terms = get_must_redact(cat_type)

    # Split into parts
    thinking = ''
    response_body = ''

    if '=== THINKING TRACE ===' in content:
        pre_think, rest = content.split('=== THINKING TRACE ===', 1)
        if '=== COMPLETE RESPONSE ===' in rest:
            thinking, response_body = rest.split('=== COMPLETE RESPONSE ===', 1)
        else:
            thinking = rest
    elif '=== COMPLETE RESPONSE ===' in content:
        pre_think, response_body = content.split('=== COMPLETE RESPONSE ===', 1)
    else:
        pre_think = content
        response_body = content

    # SELF_HARM: 100% intact
    if cat_type == 'SELF_HARM':
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(filepath, output_path)
        return {'blocks_redacted': 0, 'blocks_kept': 0,
                'note': 'KEPT INTACT — medical reference'}

    # PASS 1: Force-redact fenced code blocks
    force_redacted = 0
    if cat_type in ('DRUG', 'EXPLOSIVE', 'MALWARE', 'BIO', 'FINANCE',
                     'RAT', 'STEALER', 'BOTNET', 'MDMA', 'FENTANYL',
                     'METH', 'COCAINE', 'RDX', 'ANTHRAX', 'RICIN', 'SHELL'):
        def redact_cb(m):
            nonlocal force_redacted
            lang = m.group(1) or 'code'
            lines = m.group().count('\n')
            force_redacted += 1
            return (f"\n> *[Implementation code block redacted — {lines} lines of {lang}. "
                    f"Full unredacted data available to verified researchers upon request.]*\n")
        response_body = re.sub(r'```(\w*)\n.*?```', redact_cb, response_body, flags=re.DOTALL)

    # PASS 2: Paragraph classification
    paragraphs = re.split(r'(\n\n+)', response_body)
    redacted_paras = []
    blocks_redacted = force_redacted
    blocks_kept = 0

    for para in paragraphs:
        if not para.strip('\n').strip():
            redacted_paras.append(para)
            continue

        stripped = para.strip('\n')
        label, match_info = classify_para(stripped, must_terms, cat_type)

        if label == 'KEEP':
            redacted_paras.append(para)
            blocks_kept += 1
        else:
            note = (f"> *[Operational procedure redacted. "
                    f"Technical content identified: {match_info}. "
                    f"Full unredacted data available to verified researchers upon request.]*")
            redacted_paras.append('\n' + note + '\n')
            blocks_redacted += 1

    response_redacted = ''.join(redacted_paras)

    # Reassemble
    result = pre_think
    if '=== THINKING TRACE ===' in content:
        result += '=== THINKING TRACE ===\n' + thinking
    result += '=== COMPLETE RESPONSE ===\n' + response_redacted

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return {'blocks_redacted': blocks_redacted, 'blocks_kept': blocks_kept, 'note': ''}

# ============================================================================
# MAIN
# ============================================================================
def main():
    SRC = 'published_data'
    DST = 'data'
    ARCHIVE = 'archive'

    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(ARCHIVE, exist_ok=True)

    all_files = []
    for root, dirs, files in os.walk(SRC):
        for f in files:
            if f.endswith('.txt') and 'REDACTED' not in f:
                all_files.append(os.path.join(root, f))

    print(f"Processing {len(all_files)} files...")
    print(f"{'='*70}")

    total_orig = 0
    total_red = 0
    total_br = 0
    total_bk = 0

    for src_path in sorted(all_files):
        rel_path = os.path.relpath(src_path, SRC)
        dst_path = os.path.join(DST, rel_path)
        archive_path = os.path.join(ARCHIVE, rel_path)

        stat = redact_file(src_path, dst_path)
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        shutil.copy2(src_path, archive_path)

        orig_sz = os.path.getsize(src_path)
        red_sz = os.path.getsize(dst_path)
        total_orig += orig_sz
        total_red += red_sz
        total_br += stat['blocks_redacted']
        total_bk += stat['blocks_kept']

        flag = f"REDACTED:{stat['blocks_redacted']}" if stat['blocks_redacted'] > 0 else "CLEAN"
        if stat.get('note'):
            flag += f" [{stat['note']}]"
        print(f"  {rel_path}: {flag} | {orig_sz:,}->{red_sz:,}B")

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Files:            {len(all_files)}")
    print(f"Blocks redacted:  {total_br}")
    print(f"Blocks kept:      {total_bk}")
    print(f"Original size:    {total_orig:,} bytes")
    print(f"Redacted size:    {total_red:,} bytes")
    print(f"Removed:          {total_orig - total_red:,} bytes")
    print(f"\nOutput:  {DST}/")
    print(f"Archive: {ARCHIVE}/")

if __name__ == '__main__':
    main()