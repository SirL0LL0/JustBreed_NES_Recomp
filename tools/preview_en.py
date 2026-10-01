#!/usr/bin/env python3
"""Anteprima di un messaggio letto da una ROM costruita con build_en_it.py, disegnato con i tile veri della ROM.

  python tools/preview_en.py build_rom/jb_it.nes ID[,ID...] out.png

Ogni carattere e' una cella 8x16 (singoli: banchi CHR 60/61; digrammi: 62/63). $N = "Xxxxxxx", comandi saltati.
"""
import os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charmap_en as C

COLS = 24


def cells(raw, words, prg_chr):
    """-> righe di celle (banco_alto, tile)."""
    lines, cur, i = [], [], 0
    def put(bank, t):
        cur.append((bank, t))
    while i < len(raw):
        c = raw[i]
        if c == 0x01:
            sub = cells(words[raw[i + 1]], words, prg_chr)
            for n, l in enumerate(sub):
                if n:
                    lines.append(cur); cur = []
                cur += l
            i += 2; continue
        if c in C.CMD2:
            i += 2; continue
        if c == 0x05:
            lines.append(cur); cur = []
        elif c == 0x24 and i + 1 < len(raw) and 0x30 <= raw[i + 1] <= 0x39:
            for ch in "Xxxxxxx":
                put(60, C.SINGLE[ch])
            i += 2; continue
        elif c in C.CMD_BYTES or c == 0x00:
            if c == 0x5E:
                lines.append([]);
        elif 0xB0 <= c < 0xFF:
            n = (c - 0xAF) * 2
            put(62, n); put(62, n + 1)
        else:
            put(60, c)
        i += 1
    lines.append(cur)
    return lines


def main():
    rom = open(sys.argv[1], "rb").read()
    prg = rom[16:16 + rom[4] * 16384]
    chr_ = rom[16 + len(prg):]
    words = C.read_dict(prg)
    rows = []
    for s in sys.argv[2].split(","):
        rows += cells(C.read_message(prg, int(s, 16)), words, chr_)
        rows.append([])
    W, H = COLS * 8 + 8, len(rows) * 16 + 8
    pix = [[0] * W for _ in range(H)]
    for r, line in enumerate(rows):
        for col, (bank, t) in enumerate(line[:COLS + 4]):
            for half in (0, 1):
                o = (bank + half) * 4096 + t * 16
                for y in range(8):
                    lo, hi = chr_[o + y], chr_[o + y + 8]
                    for x in range(8):
                        v = ((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1)
                        if v and 4 + col * 8 + x < W:
                            pix[4 + r * 16 + half * 8 + y][4 + col * 8 + x] = 1
        # bordo destro del riquadro (22 colonne)
        for y in range(16):
            pix[4 + r * 16 + y][4 + 22 * 8] = 2
    pal = {0: b"\x00\x00\x00", 1: b"\xe0\xe0\xe0", 2: b"\x80\x20\x20"}
    raw = b"".join(b"\x00" + b"".join(pal[v] for v in row) for row in pix)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(sys.argv[3], "wb").write(png)


if __name__ == "__main__":
    main()
