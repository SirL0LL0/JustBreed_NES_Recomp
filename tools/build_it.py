#!/usr/bin/env python3
"""Costruisce la ROM di prova in italiano a partire dalla ROM giapponese.

  python tools/build_it.py baserom_jp.nes text/it_wrapped.tsv out.nes

* sostituisce albero, tabella puntatori e blob dei dialoghi (banchi 46 e 16-26) con quelli italiani;
  i messaggi non ancora tradotti diventano un segnaposto "Msg NNNN" per non mescolare l'alfabeto giapponese;
* ridisegna nel CHR (banchi 60/61) i glifi latini dal font Unscii (pubblico dominio, assets/unscii-16.hex).
Poi verifica che la routine originale del gioco (py65) decodifichi tutti i messaggi come atteso.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hufpack, charmap_it
from dialog_decode import Game

UNIT = 8192
here = os.path.dirname(os.path.abspath(__file__))


def load_unscii():
    d = {}
    for l in open(os.path.join(here, "..", "assets", "unscii-16.hex")):
        if ":" in l:
            a, b = l.strip().split(":")
            if len(b) == 32:
                d[int(a, 16)] = bytes.fromhex(b)
    return d


def patch_font(data, prg_size):
    uns = load_unscii()
    chr0 = 16 + prg_size
    n = 0
    for tile_id, ch in charmap_it.DRAW.items():
        g = uns.get(ord(ch))
        if g is None:
            raise ValueError("Unscii non ha il glifo %r" % ch)
        for half, bank in ((0, 60), (1, 61)):
            rows = g[half * 8:half * 8 + 8]
            o = chr0 + bank * 4096 + tile_id * 16
            for y, byte in enumerate(rows):
                data[o + y] = byte           # piano 0
                data[o + 8 + y] = byte       # piano 1 -> colore 3
        n += 1
    return n


# Tabelle di nomi a record fissi: nome -> (offset PRG, larghezza record in byte, numero record)
# Il record e' 'testo + spazi' fino a larghezza-1 colonne, poi 00 (kanji = 2 colonne, come nell'originale).
TABLES = {"items": (0x4C000, 8, 154), "spells": (0x4C4D0, 8, 74), "places": (0x4D2B4, 10, 29), "chars": (0x72000, 6, 37), "ranks": (0x747C4, 8, 4)}


def patch_tables(data, tsv_path):
    n = 0
    for l in open(tsv_path, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) < 3 or p[0] == "table":
            continue
        tab, idx, text = p[0], int(p[1]), p[2]
        base, width, count = TABLES[tab]
        if not 0 <= idx < count:
            raise ValueError("%s: id %d fuori tabella" % (tab, idx))
        if tab == "chars" and idx == count - 1:
            width = 5                       # l'ultimo record e' di 5 byte: subito dopo iniziano i nomi dei mostri
        raw = charmap_it.encode_text(text)
        if len(raw) > width - 1:
            raise ValueError("%s[%d] %r: %d colonne (max %d)" % (tab, idx, text, len(raw), width - 1))
        rec = raw + b"\x20" * (width - 1 - len(raw)) + b"\x00"
        off = 16 + base + idx * width
        data[off:off + width] = rec
        n += 1
    return n


# Schermata di scelta del nome (unita' 58, CPU $8000): griglia 10 colonne x 6 righe, cursore X = riga*10+colonna.
# Il testo della griglia e' una stringa inline ($8E87) di celle "20 xx"; la tabella X -> carattere e' a $90B6;
# X=$39/$3A erano i tasti dakuten/handakuten (X-0x70 / X-0x75 sul codice), X=$3B e' "fine".
# Italiano: colonne 0-4 maiuscole, 5-9 minuscole; il dakuten diventa una cella normale; SELECT (cambio kana) disattivato.
NAME_UNIT = 58
GRID_STR = 0x8E87                      # primo byte dopo JSR $97CF
GRID_ROWS = ["ABCDE" "abcde", "FGHIJ" "fghij", "KLMNO" "klmno", "PQRST" "pqrst", "UVWXY" "uvwxy",
             "Z'-.!" "zéàè"]           # 5 righe da 10 + riga finale da 9 celle (+ "Fin" alla cella 59)


def patch_name_grid(data):
    base = 16 + NAME_UNIT * UNIT - 0x8000
    def cell(ch): return charmap_it.IT[ch]
    cells = [cell(c) for row in GRID_ROWS for c in row]
    assert len(cells) == 59
    # stringa inline: 5 righe da 10 celle, riga 6 da 9 celle + " Fin", ogni riga chiusa da 05
    s = bytearray()
    for r in range(5):
        for c in cells[r * 10:r * 10 + 10]:
            s += bytes([0x20, c])
        s.append(0x05)
    for c in cells[50:59]:
        s += bytes([0x20, c])
    s += bytes([0x20]) + charmap_it.encode_text("Fin") + bytes([0x05])
    old_end = data.index(b"\x05\x00", base + GRID_STR) + 1        # il 05 finale, poi il 00 terminatore
    assert old_end - (base + GRID_STR) == len(s), "lunghezza griglia diversa: %d/%d" % (old_end - base - GRID_STR, len(s))
    assert data[base + GRID_STR - 3:base + GRID_STR] == bytes([0x20, 0xCF, 0x97])
    data[base + GRID_STR:base + GRID_STR + len(s)] = s
    # tabella cella -> codice (58 celle di carattere; la 59a e' "fine")
    t = base + 0x90B6
    assert data[t] == 0x71
    data[t:t + 59] = bytes(cells)
    # dakuten/handakuten: i confronti CPX #$3A ($8FE7) e CPX #$39 ($901A) non devono piu' scattare
    for a, v in ((0x8FE7, 0x3A), (0x901A, 0x39)):
        assert data[base + a:base + a + 2] == bytes([0xE0, v]), hex(a)
        data[base + a + 1] = 0xFF
    # SELECT: BMI $8FCE (30 xx a $8FB7) -> NOP NOP
    assert data[base + 0x8FB7] == 0x30
    data[base + 0x8FB7:base + 0x8FB9] = b"\xEA\xEA"


# Blocchi di testo inline a lunghezza fissa (righe terminate da 00, ultima riga vuota = fine): nome -> (offset PRG, byte)
BLOCKS = {"intro": (0x4AB37, 226), "monsters": (0x73D77, 649)}


def patch_blocks(data, tsv_dir):
    n = 0
    for name, (off, size) in BLOCKS.items():
        p = os.path.join(tsv_dir, name + "_it.tsv")
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8-sig").read().split("\n")
        if lines and lines[-1] == "":
            lines.pop()                                  # newline finale del file
        raw = b"".join(charmap_it.encode_text(l) + b"\x00" for l in lines)
        if len(raw) > size:
            raise ValueError("blocco %s: %d byte (max %d)" % (name, len(raw), size))
        data[16 + off:16 + off + size] = raw + bytes(size - len(raw))
        n += 1
    return n


def patch_monster_ptr(data):
    """La routine unit57:$9727 cerca i nomi dei mostri saltando N stringhe a partire da $80D8 (LDA #$D8 / LDA #$80).
    I nomi italiani sono piu' lunghi: la nuova tabella sta nella coda libera dell'unita' 57, a $9D77."""
    base = 16 + 57 * UNIT - 0x8000
    assert data[base + 0x972B:base + 0x972D] == bytes([0xA9, 0xD8]) and data[base + 0x972F:base + 0x9731] == bytes([0xA9, 0x80])
    data[base + 0x972C] = 0x77
    data[base + 0x9730] = 0x9D


# Messaggi di fine battaglia (unita' 59): NON fanno parte del sistema Huffman dei dialoghi. Sono testo incorporato
# direttamente nel flusso di codice, dopo "jsr $9E01" (unit58:$9E01: legge la stringa a cui il chiamante ha appena
# saltato, la stampa carattere per carattere fino allo 0x00, poi riprende l'esecuzione da li' - vedi disasm/unit58.asm).
# Il ritorno e' calcolato dinamicamente (JMP (BE) dopo aver trovato lo 0x00): un testo piu' corto dell'originale va
# bene, PIU' LUNGO no (sovrascriverebbe l'istruzione vera che segue). "budget" = byte totali disponibili (originale
# giapponese compreso 0x00), verificato scorrendo disasm/unit59.asm dal punto della jsr fino alla prossima istruzione
# reale. mai giocate/verificate a schermo: il gioco le stampa solo a fine round di combattimento.
BATTLE_MESSAGES = [
    # (unita, offset dall'inizio unita (unit*UNIT), testo italiano, budget byte incl. 0x00, byte JP attesi per la verifica)
    # JP: "$2は $0のけいけんちをえた" / "$2は $0Gのおかねをえた" / "$2は レベルがあがった" / "$0は $2の魔法をおぼえた"
    (59, 0x58A, "$2 vince $0 ESP<05>", 17, bytes.fromhex("24328a202430897972799d816674800500")),
    (59, 0x5F9, "$2 vince $0<47><05>", 16, bytes.fromhex("24328a20243047897576886674800500")),
    (59, 0x65D, "$2 sale liv!<05>", 14, bytes.fromhex("24328a20dafdd90671066f800500")),
    (59, 0x88D, "$0 apprende $2<05>", 18, bytes.fromhex("24308a202432890108010a66751e74800500")),
]
# Codici che la routine di stampa (unit58:$9E13, tabella a $9E3A) tratta come COMANDI e non come caratteri:
# "+" (0x2B) per esempio salta a un'altra routine e fa stampare un dialogo a caso. 0x24 ("$N" = variabile) e' voluto.
BATTLE_CMD_BYTES = {0x5E, 0x25, 0x23, 0x2E, 0x2B, 0x2D, 0x26, 0x40, 0x2A, 0x2F, 0x3E, 0x41, 0x42, 0x43, 0x44,
                    0x1F, 0x46, 0x3B, 0x49}


def patch_battle_messages(data):
    """Scrive i messaggi di BATTLE_MESSAGES sopra il testo giapponese, entro il budget di byte disponibile
    (il resto, se avanza spazio, resta a 0x00: byte morti, mai raggiunti dall'esecuzione)."""
    n = 0
    for unit, off, text, budget, jp_expected in BATTLE_MESSAGES:
        base = 16 + unit * UNIT + off
        got = bytes(data[base:base + len(jp_expected)])
        assert got == jp_expected, (
            "battle msg unit %d off 0x%04X: atteso %s, trovato %s (ROM diversa da quella prevista?)" %
            (unit, off, jp_expected.hex(" "), got.hex(" ")))
        enc = charmap_it.encode_text(text) + b"\x00"
        assert len(enc) <= budget, "messaggio troppo lungo: %r (%d byte, budget %d)" % (text, len(enc), budget)
        for i, b in enumerate(enc):
            if i and enc[i - 1] == 0x24:
                continue                                    # la cifra dopo "$"
            assert b not in BATTLE_CMD_BYTES, "%r: il byte 0x%02X e' un comando della routine di stampa" % (text, b)
        data[base:base + len(enc)] = enc
        data[base + len(enc):base + budget] = bytes(budget - len(enc))
        n += 1
    return n


import re
_TOKEN = re.compile(r"\{[0-9A-F]{2}:[0-9A-F]{2}\}|<[0-9A-F]{2}>|\$\d|#!?\d+|\*\.?\d+|[+\-%&]\d+|\.\d+")
_JPTEXT = re.compile(r"[぀-ヿ一-鿿＀-￯…「-』・]")


def placeholder(jp_display, mid):
    """Messaggio non ancora tradotto: tiene TUTTE le righe di comando (#!.., *.., +n, %n, ...) che pilotano il gioco
    e sostituisce il testo con una sola riga 'Msg NNNN'. Senza i comandi la storia non avanza."""
    out, placed = [], False
    for l in jp_display.split("<05>"):
        if _JPTEXT.search(_TOKEN.sub("", l)):
            if not placed:
                out.append("“Msg %04X”" % mid)
                placed = True
        elif l.strip() == "<5E>":
            continue
        else:
            out.append(l)
    return "<05>".join(out)


def main():
    rom_path, tsv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    data = bytearray(open(rom_path, "rb").read())
    prg_size = data[4] * 16384
    jp = [l.rstrip("\n").split("\t") for l in open(os.path.join(here, "..", "text", "dialog_jp.tsv"), encoding="utf-8")][1:]
    ids = [int(r[0], 16) for r in jp]
    it = {}
    for l in open(tsv, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 2 and p[0] != "id":
            it[int(p[0], 16)] = p[1]
    alloc = {}
    if "--no-vwf" not in sys.argv:
        import vwf
        alloc = vwf.alloc_from_dialog(os.path.join(here, "..", "text", "it.tsv"))
        print("VWF: %d coppie di celle precomposte" % len(alloc))
    msgs, done = [], 0
    jpd = {int(r[0], 16): r[2] for r in jp}
    for mid in ids:
        if mid in it:
            msgs.append(charmap_it.encode_text(it[mid], alloc)); done += 1
        else:
            msgs.append(charmap_it.encode_text(placeholder(jpd[mid], mid), alloc))
    print("messaggi: %d (tradotti %d)" % (len(ids), done))

    tree, blobs, codes = hufpack.encode_messages(msgs)
    assert len(tree) <= 512, "albero troppo grande: %d" % len(tree)
    # Regioni libere per i blob: unita' 16-27 (27 e' vuota nel gioco originale) + code libere (FF/00) delle unita' 28-31.
    regions = [(0, 12 * UNIT)]
    for u in (28, 29, 30, 31):
        seg = data[16 + u * UNIT:16 + (u + 1) * UNIT]
        t = len(seg)
        while t > 0 and seg[t - 1] in (0, 0xFF):
            t -= 1
        start = t + 16 + ((t + 16) & 1)                     # 16 byte di margine, allineato a 2
        if start < UNIT - 64:
            regions.append(((u - 16) * UNIT + start, (u - 16) * UNIT + UNIT))
    pos, used = hufpack.layout_regions(blobs, regions)
    print("albero %d byte, %d simboli; blob %d byte (%.1f unita'; regioni libere %d byte)" % (
        len(tree), len(codes), used, used / UNIT, sum(hi - lo for lo, hi in regions)))
    assert max(len(b) for b in blobs) <= 256, "blob > 256 byte: id %04X (%d)" % (
        ids[max(range(len(blobs)), key=lambda i: len(blobs[i]))], max(len(b) for b in blobs))

    def wr(unit, off, b):
        data[16 + unit * UNIT + off:16 + unit * UNIT + off + len(b)] = b

    wr(46, 0, tree + bytes(512 - len(tree)))
    for i, mid in enumerate(ids):
        wr(46, 0x200 + mid, hufpack.pointer_entry(pos[i]))
    for i, b in enumerate(blobs):
        for k, byte in enumerate(b):
            p = pos[i] + k
            data[16 + (16 + p // UNIT) * UNIT + p % UNIT] = byte
    print("glifi latini ridisegnati:", patch_font(data, prg_size))
    if alloc:
        print("glifi VWF (coppie):", vwf.patch_pair_glyphs(data, prg_size, alloc))
    up = os.path.join(here, "..", "text", "ui_it.tsv")
    if os.path.exists(up):
        import ui_patch
        n, nb = ui_patch.apply_ui(data, up)
        print("stringhe di interfaccia tradotte: %d (%d byte in unita' 47)" % (n, nb))
    tp = os.path.join(here, "..", "text", "tables_it.tsv")
    if os.path.exists(tp):
        print("voci di tabella tradotte:", patch_tables(data, tp))
    print("blocchi di testo:", patch_blocks(data, os.path.join(here, "..", "text")))
    if os.path.exists(os.path.join(here, "..", "text", "monsters_it.tsv")):
        patch_monster_ptr(data)
    patch_name_grid(data)
    print("griglia nomi: latina")
    print("messaggi di fine battaglia tradotti:", patch_battle_messages(data))
    open(out, "wb").write(data)
    print("scritta", out)

    g = Game(out)
    bad = 0
    for mid, m in zip(ids, msgs):
        got = g.message(mid)
        if got != m:
            bad += 1
            if bad <= 3:
                print("  diverso %04X: atteso %s ottenuto %s" % (mid, m.hex(), got.hex()))
    print("verifica decodifica con la routine del gioco: %d messaggi, diversi: %d" % (len(ids), bad))


if __name__ == "__main__":
    main()




