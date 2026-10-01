#!/usr/bin/env python3
"""Estrae il copione della traduzione inglese (baserom.nes) in un TSV leggibile.

  python tools/en_extract.py baserom.nes text/en.tsv

Colonne: indice messaggio (hex, = offset nella tabella dei puntatori), byte grezzi (hex), testo.
La patch inglese salva i messaggi NON compressi (vedi charmap_en.py): si leggono direttamente dalla ROM tramite
puntatore + tabella dei banchi, fino a 00 00 (uno 00 singolo separa le parti di un messaggio: <00> nel testo).
Il testo espande digrammi e parole del dizionario. Scrive anche <out>_dict.tsv con il dizionario.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charmap_en

d = open(sys.argv[1], "rb").read()
prg = d[16:16 + d[4] * 16384]
words = charmap_en.read_dict(prg)
out = open(sys.argv[2], "w", encoding="utf-8", newline="\n")
for idx in range(0, 2 * charmap_en.N_MSG, 2):
    raw = charmap_en.read_message(prg, idx)
    out.write("%04X\t%s\t%s\n" % (idx, raw.hex(), charmap_en.render(raw, words)))
print("messaggi:", charmap_en.N_MSG, " parole nel dizionario:", len(words))
dw = open(os.path.splitext(sys.argv[2])[0] + "_dict.tsv", "w", encoding="utf-8", newline="\n")
for i, w in enumerate(words):
    dw.write("%02X\t%s\t%s\n" % (i, w.hex(), charmap_en.render(w)))
