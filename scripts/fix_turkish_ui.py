#!/usr/bin/env python3
import glob, re, os

replacements = {
    r"\bGorevler\b": 'Görevler',
    r"\bGorev\b": 'Görev',
    r"\bCikis\b": 'Çıkış',
    r"\bYeni Gorev Ekle\b": 'Yeni Görev Ekle',
    r"\bBaslik\b": 'Başlık',
    r"\bAciklama\b": 'Açıklama',
    r"\bOncelik\b": 'Öncelik',
    r"\bIptal\b": 'İptal',
    r"\bYuksek\b": 'Yüksek',
    r"\bDusuk\b": 'Düşük'
}

files = glob.glob('templates/**/*.html', recursive=True) + glob.glob('templates/*.html')
changed = []
for p in files:
    with open(p, 'r', encoding='utf-8') as f:
        s = f.read()
    orig = s
    for pat, repl in replacements.items():
        s = re.sub(pat, repl, s)
    if s != orig:
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(s)
        changed.append(p)

print('Updated files:', changed)
