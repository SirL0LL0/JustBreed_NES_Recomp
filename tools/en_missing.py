#!/usr/bin/env python3
"""Elenca i messaggi di text/en.tsv che contengono testo (parole) ma non sono in text/it_en(.tsv|/*.tsv)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_en_it import load_texts

here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "text")
en, it = load_texts(os.path.join(here, "en.tsv"), os.path.join(here, "it_en.tsv"))
n = 0
for k in sorted(en):
    if k in it:
        continue
    vis = re.sub(r"<[0-9A-F]{2}>[0-9!. ]*|\{[0-9A-F]{2}:[0-9A-F]{2}\}|\$\d", " ", en[k])
    if re.search(r"[A-Za-z]{3,}", vis):
        print("%04X\t%s" % (k, en[k]))
        n += 1
print("messaggi con testo non tradotti:", n)
