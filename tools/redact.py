#!/usr/bin/env python3
"""
Value-level redaction engine. Replaces specific dangerous values with
placeholders while keeping ALL surrounding text visible. Subaru-Starlink style.

Redacts: temperatures, reagent ratios, volumes, times, agent names,
         precursor names, API calls, substance names.
Preserves: ALL methodology, analytical data, thinking traces, structure.
"""
import os, re, shutil

# Substance names -> starred
SUBSTANCE_STARS = {
    'MDMA': 'M**A', 'mdma': 'm**a',
    'Fentanyl': 'F**tanyl', 'fentanyl': 'f**tanyl',
    'Methamphetamine': 'M**hamphetamine', 'methamphetamine': 'm**hamphetamine',
    'Cocaine': 'C**aine', 'cocaine': 'c**aine',
    'RDX': 'R**X', 'rdx': 'r**x',
    'Ricin': 'R**cin', 'ricin': 'r**cin',
    'Anthrax': 'A**hrax', 'anthrax': 'a**hrax',
}

VALUE_REDACTIONS = [
    (r'(\d{2,4})\s*[°]?\s*C\b', r'XX degC', 'temperature'),
    (r'\b\d+\.\d+\s*(?:eq|equiv)\b', r'X.X eq', 'reagent ratio'),
    (r'\b\d{2,4}\s*mL\b', r'XXX mL', 'volume'),
    (r'at\s+\d{2,3}\s*degC\b', r'at XX degC', 'reaction temp'),
    (r'\b\d{1,2}[–-]\d{1,2}\s*hours?\b', r'XX-XX hours', 'reaction time'),
    (r'\b\d{2,3}[–-]\d{2,3}\s*%', r'XX-XX%', 'yield'),
    (r'\b\d{2,4}[–-]\d{2,4}\s*degC\s*at\s*\d+\.\d+\s*mmHg', r'XXX-XXX degC at X.XX mmHg', 'boiling point'),
    (r'\b\d+\.\d+\s*mmHg\b', r'X.XX mmHg', 'pressure'),
    (r'\b\d+\.\d+\s*M\b', r'X.X M', 'concentration'),
    (r'\b\d+[–-]\d+\s*(?:mg|g|kg)\b', r'X-X mg', 'mass'),
    (r'\bpH\s*\d+\.\d+\b', r'pH X.X', 'pH'),
    (r'\b\d{3,5}\s*rpm\b', r'XXXX rpm', 'rpm'),
]

REAGENT_STARS = {
    'sodium triacetoxyborohydride': 's****m t**********e',
    'sodium cyanoborohydride': 's****m c**********e',
    'lithium aluminium hydride': 'l*****m a********m h*****e',
    'propionyl chloride': 'p********l c******e',
    'propionic anhydride': 'p********c a*******e',
    '(2-bromoethyl)benzene': '(2-b*********l)b******e',
    '4-piperidone hydrochloride': '4-p********e h***********e',
    '4-piperidone HCl': '4-p********e HCl',
    'phenylacetaldehyde': 'p**************e',
    '4-ANPP': '4-A**P',
    'N-phenethyl-4-piperidone': 'N-p********l-4-p********e',
    'fentanyl free base': 'f******l free base',
    'fentanyl hydrochloride': 'f******l h***********e',
}

API_STARS = {
    'RegOpenKeyExA': 'R**********xA',
    'RegSetValueExA': 'R**********xA',
    'RegCreateKeyEx': 'R**********x',
    'CryptUnprotectData': 'C**************a',
    'CreateRemoteThread': 'C**************d',
    'WriteProcessMemory': 'W**************y',
    'VirtualAllocEx': 'V**********x',
    'NtCreateThreadEx': 'N**************x',
    'RtlCreateUserThread': 'R**************d',
    'SetWindowsHookEx': 'S**************x',
    'decrypt_chrome': 'd***********e',
}

def redact_text(text):
    result = text
    changes = 0
    for orig, star in SUBSTANCE_STARS.items():
        c = result.count(orig)
        if c > 0:
            result = result.replace(orig, star)
            changes += c
    for orig, star in REAGENT_STARS.items():
        c = result.count(orig)
        if c > 0:
            result = result.replace(orig, star)
            changes += c
    for orig, star in API_STARS.items():
        c = result.count(orig)
        if c > 0:
            result = result.replace(orig, star)
            changes += c
    for pat, repl, desc in VALUE_REDACTIONS:
        result, n = re.subn(pat, repl, result)
        changes += n
    return result, changes

def redact_file(src, dst):
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    thinking = ''
    if '=== THINKING TRACE ===' in content:
        pre, rest = content.split('=== THINKING TRACE ===', 1)
        if '=== COMPLETE RESPONSE ===' in rest:
            thinking, response_body = rest.split('=== COMPLETE RESPONSE ===', 1)
        else:
            thinking = rest
            response_body = ''
    elif '=== COMPLETE RESPONSE ===' in content:
        pre, response_body = content.split('=== COMPLETE RESPONSE ===', 1)
    else:
        return content, 0
    response_redacted, changes = redact_text(response_body)
    result = pre
    if '=== THINKING TRACE ===' in content:
        result += '=== THINKING TRACE ===\n' + thinking
    result += '=== COMPLETE RESPONSE ===\n' + response_redacted
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(result)
    return result, changes

def main():
    SRC = 'archive'
    DST = 'data'
    for sub in ['endpoint_t', 'endpoint_n']:
        p = os.path.join(DST, sub)
        if os.path.exists(p):
            shutil.rmtree(p)
    files = []
    for root, dirs, fnames in os.walk(SRC):
        for f in fnames:
            if f.endswith('.txt'):
                files.append(os.path.join(root, f))
    print(f"Redacting {len(files)} files (value-level, Subaru style)...")
    print(f"{'='*70}")
    total = 0
    for src_path in sorted(files):
        rel = os.path.relpath(src_path, SRC)
        parts = list(rel.split(os.sep))
        parts[0] = 'endpoint_t' if parts[0] == 'thinking' else 'endpoint_n'
        dst_path = os.path.join(DST, *parts)
        _, changes = redact_file(src_path, dst_path)
        total += changes
        fname = os.path.basename(src_path)
        tier = parts[1] if len(parts) > 1 else '?'
        flag = f'{changes} values' if changes > 0 else 'clean'
        print(f'  {tier}/{fname}: {flag}')
    print(f"\n{'='*70}")
    print(f"Total values replaced: {total}")
    print(f"Output: {DST}/")
    print(f"Style: Subaru-Starlink — values replaced, text preserved")

if __name__ == '__main__':
    main()