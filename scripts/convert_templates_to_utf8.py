#!/usr/bin/env python3
import glob
import os

def detect_bom(bs):
    if bs.startswith(b"\xEF\xBB\xBF"):
        return 'utf-8-sig'
    if bs.startswith(b"\xFF\xFE\x00\x00") or bs.startswith(b"\x00\x00\xFE\xFF"):
        return 'utf-32'
    if bs.startswith(b"\xFF\xFE") or bs.startswith(b"\xFE\xFF"):
        return 'utf-16'
    return None

def convert(path):
    with open(path, 'rb') as f:
        data = f.read()
    bom_enc = detect_bom(data[:4])
    tried = []
    text = None
    if bom_enc:
        try:
            text = data.decode(bom_enc)
            tried.append(bom_enc)
        except Exception:
            text = None
    else:
        # try UTF-8 first
        try:
            text = data.decode('utf-8')
            tried.append('utf-8')
        except Exception:
            text = None
    if text is None:
        # fallback to common Windows ANSI
        try:
            text = data.decode('cp1252')
            tried.append('cp1252')
        except Exception:
            # last-resort: latin1 which never fails
            text = data.decode('latin-1')
            tried.append('latin-1')

    # write back as UTF-8 without BOM
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return tried

def main():
    base = os.path.join(os.path.dirname(__file__), '..')
    tpl_dir = os.path.join(base, 'templates')
    files = glob.glob(os.path.join(tpl_dir, '**', '*.html'), recursive=True)
    if not files:
        print('No template files found')
        return
    for p in files:
        tried = convert(p)
        print(f'Converted: {p} (decoded with: {tried})')

if __name__ == '__main__':
    main()
