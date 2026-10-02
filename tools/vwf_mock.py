#!/usr/bin/env python3
"""Anteprima di come apparirebbe un messaggio col VWF statico (celle da 8 pixel con 1 o 2 caratteri).

  python tools/vwf_mock.py build_rom/jb_it.nes ID maxw cols out.png

maxw = larghezza massima delle lettere (6 = font attuale, 5 = font assottigliato); cols = colonne del riquadro.
Il testo del messaggio viene ri-impaginato a parole contando le CELLE (coppie unite quando stanno in 8 pixel).
"""
import os, re, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charmap_en as C
from build_en_it import load_texts
import menu_words as M

rom = bytearray(open(sys.argv[1], "rb").read())
PRG = 512 * 1024
msg, maxw, cols, out = int(sys.argv[2], 16), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]


def glyph(ch):
    if ch == " ":
        return [[0, 0, 0] for _ in range(16)]
    g = M._regular(rom, PRG, ch)
    while len(g[0]) > maxw:                     # assottiglia togliendo colonne ridondanti
        w = len(g[0])
        best, score = 1, -1
        for x in range(1, w - 1):
            s = max(sum(r[x] == r[x - 1] for r in g), sum(r[x] == r[x + 1] for r in g))
            if s > score:
                best, score = x, s
        g = [r[:best] + r[best + 1:] for r in g]
    return g


def cells_of(word):
    """parola -> lista di celle (ognuna 1 o 2 caratteri), unione golosa."""
    out, i = [], 0
    while i < len(word):
        if i + 1 < len(word):
            a, b = glyph(word[i]), glyph(word[i + 1])
            gap = 0 if " " in word[i:i + 2] else 1
            if len(a[0]) + gap + len(b[0]) <= 8:
                out.append(word[i:i + 2]); i += 2; continue
        out.append(word[i]); i += 1
    return out


def cell_img(cell):
    gs = [glyph(c) for c in cell]
    img = [[0] * 8 for _ in range(16)]
    if len(gs) == 1:
        g = gs[0]; x0 = 1 if len(g[0]) <= 6 else 0
        for y in range(16):
            for i, v in enumerate(g[y]):
                if v and x0 + i < 8:
                    img[y][x0 + i] = 1
        return img
    a, b = gs
    gap = 0 if " " in cell else 1
    x = 0
    for g in (a, b):
        for y in range(16):
            for i, v in enumerate(g[y]):
                if v and x + i < 8:
                    img[y][x + i] = 1
        x += len(g[0]) + gap
    return img


here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "text")
en, it = load_texts(os.path.join(here, "en.tsv"), os.path.join(here, "it_en.tsv"))
text = it[msg]
text = re.sub(r"<(?!05>|5E>)[0-9A-F]{2}>[0-9!. ]*|\{[0-9A-F]{2}:[0-9A-F]{2}\}", "", text).replace("$1", "LOllo")
pages = [p.replace("<05>", " ").split() for p in text.split("<5E>")]
lines = []
for words in pages:
    cur = []
    for w in words:
        cand = (" ".join(cur + [w]))
        if len(cells_of(cand)) <= cols or not cur:
            cur.append(w)
        else:
            lines.append(cells_of(" ".join(cur))); cur = [w]
    if cur:
        lines.append(cells_of(" ".join(cur)))
    lines.append(None)
W, H = cols * 8 + 16, len(lines) * 16 + 16
pix = [[0] * W for _ in range(H)]
for r, line in enumerate(lines):
    if line is None:
        continue
    for c, cell in enumerate(line):
        im = cell_img(cell)
        for y in range(16):
            for x in range(8):
                if im[y][x]:
                    pix[8 + r * 16 + y][8 + c * 8 + x] = 1
for y in range(H):
    pix[y][8 + cols * 8] = 2
pal = {0: b"\x00\x00\x00", 1: b"\xe0\xe0\xe0", 2: b"\x80\x20\x20"}
raw = b"".join(b"\x00" + b"".join(pal[v] for v in row) for row in pix)
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
open(out, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
                      chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
print("righe:", sum(1 for l in lines if l), "celle max:", max(len(l) for l in lines if l))
