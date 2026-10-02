#!/usr/bin/env python3
"""Stima del guadagno di un VWF statico (due caratteri in una cella da 8 pixel) sul testo italiano.

  python tools/vwf_estimate.py build_rom/jb_it.nes

Larghezze reali dei glifi dalla ROM (colonne con inchiostro). Due caratteri stanno in una cella se
larghezza(a) + spazio + larghezza(b) <= 8 (lo spazio vale 2 pixel e non serve un pixel di separazione accanto).
Per ogni riga si unisce golosamente da sinistra; conta celle risparmiate e coppie distinte necessarie.
"""
import os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charmap_en as C
from build_en_it import load_texts

rom = bytearray(open(sys.argv[1], "rb").read())
PRG = 512 * 1024


def width(ch):
    if ch == " ":
        return 3                      # spazio minimo leggibile tra parole (2 si confonde con lo spazio tra lettere)
    code = C.SINGLE[ch]
    cols = set()
    for bank in (60, 61):
        o = 16 + PRG + bank * 4096 + code * 16
        for y in range(8):
            v = rom[o + y] | rom[o + y + 8]
            cols |= {x for x in range(8) if (v >> (7 - x)) & 1}
    return (max(cols) - min(cols) + 1) if cols else 2


MAXW = int(sys.argv[2]) if len(sys.argv) > 2 else 8      # es. 5 = simula lettere strette a 5 pixel
W = {c: min(width(c), MAXW) for c in C.SINGLE if c not in "\n"}


def fits(a, b):
    gap = 0 if " " in (a, b) else 1
    return W[a] + gap + W[b] <= 8


here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "text")
en, it = load_texts(os.path.join(here, "en.tsv"), os.path.join(here, "it_en.tsv"))
cells = saved = 0
pairs = Counter()
for k, t in it.items():
    for line in re.split(r"<05>|<5E>|<00>", t):
        vis = re.sub(r"<[0-9A-F]{2}>[0-9!. ]*|\{[0-9A-F]{2}:[0-9A-F]{2}\}|\$\d", "", line)
        vis = "".join(ch for ch in vis if ch in W)
        cells += len(vis)
        i = 0
        while i < len(vis) - 1:
            if fits(vis[i], vis[i + 1]):
                pairs[vis[i:i + 2]] += 1
                saved += 1
                i += 2
            else:
                i += 1
print("larghezze:", " ".join("%s=%d" % (c, W[c]) for c in sorted(W) if W[c] < 6))
print("celle: %d, risparmiabili: %d (%.1f%%), coppie distinte: %d" % (cells, saved, 100.0 * saved / cells, len(pairs)))
acc = 0
for n, (p, c) in enumerate(pairs.most_common(), 1):
    acc += c
    if n in (32, 64, 96, 128, 192, 256, 384):
        print("  con le %3d coppie piu' frequenti: %.1f%% delle celle" % (n, 100.0 * acc / cells))
print("piu' frequenti:", " ".join(repr(p) for p, _ in pairs.most_common(40)))
