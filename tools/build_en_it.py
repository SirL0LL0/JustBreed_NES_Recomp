#!/usr/bin/env python3
"""Traduzione italiana costruita SOPRA la traduzione inglese di Stealth (baserom.nes).

  python tools/build_en_it.py baserom.nes text/it_en.tsv build_rom/jb_it.nes

* text/it_en.tsv: "id<TAB>testo" (id = indice del messaggio come in text/en.tsv); i messaggi assenti restano
  in inglese. Formato del testo: quello di text/en.tsv (charmap_en.py): <05> a capo, <xx> comandi, $N variabili.
* ricalcola il dizionario (256 parole, codice 01 xx) sul testo finale; i digrammi (B0-FE) restano quelli inglesi;
* disegna le lettere accentate (codici 06-0C);
* scrive i messaggi nello spazio libero (unita' di testo della patch inglese + code vuote), puntatori e banchi;
* verifica: rilettura e decodifica di tutti i messaggi (anche con la routine del gioco, py65) + larghezza righe.
"""
import os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charmap_en as C

UNIT = C.UNIT
WIDTH = 22                     # colonne utili del riquadro dei dialoghi (l'inglese arriva a 22-23)
VAR_W = {"0": 7, "1": 6, "2": 7}   # larghezza stimata delle variabili $N (nomi, oggetti, numeri)


# ---------------------------------------------------------------------------------------------- testo
def load_texts(en_tsv, it_tsv):
    en = {}
    for l in open(en_tsv, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        en[int(p[0], 16)] = p[2]
    it = {}
    files = [it_tsv] if it_tsv and os.path.exists(it_tsv) else []
    more = os.path.splitext(it_tsv)[0] if it_tsv else None          # text/it_en/*.tsv: un file per blocco
    if more and os.path.isdir(more):
        files += [os.path.join(more, f) for f in sorted(os.listdir(more)) if f.endswith(".tsv")]
    for path in files:
        for l in open(path, encoding="utf-8-sig"):
            l = l.rstrip("\n")
            if not l or l.startswith("#") or "\t" not in l:
                continue
            k, v = l.split("\t", 1)
            it[int(k, 16)] = v
    return en, it


def segments(plain):
    """Divide i byte piani in pezzi: (comprimibile, bytes). Non comprimibili: comandi e loro argomenti, prefissi."""
    comp = set(C.SINGLE[c] for c in C.COMPRESSIBLE)
    out, i, cur = [], 0, bytearray()
    flag = None
    def push(f, b):
        nonlocal flag, cur
        if f != flag and cur:
            out.append((flag, bytes(cur))); cur = bytearray()
        flag = f; cur += b
    while i < len(plain):
        c = plain[i]
        if c in C.CMD2:
            push(False, plain[i:i + 2]); i += 2; continue
        if c in C.CMD_BYTES:                       # comando + eventuali argomenti (cifre, '!', '.')
            j = i + 1
            while j < len(plain) and plain[j] not in comp and plain[j] not in C.CMD_BYTES and plain[j] not in C.CMD2 \
                    and plain[j] != 0x05:
                j += 1
            push(False, plain[i:j]); i = j; continue
        push(c in comp, bytes([c])); i += 1
    if cur:
        out.append((flag, bytes(cur)))
    return out


# ------------------------------------------------------------------------------------- compressione
def choose_dict(texts, n_words=256):
    """Scelta golosa delle parole del dizionario: sottostringhe 'parola' (con spazio prima/dopo facoltativo)."""
    runs = [b for segs in texts for f, b in segs if f]
    sp = C.SINGLE[" "]
    letters = set(C.SINGLE[c] for c in C.COMPRESSIBLE if c not in " ,.")
    words = []
    marker = 0xFF                                          # segnaposto nei run gia' sostituiti
    for _ in range(n_words):
        cnt = Counter()
        for r in runs:
            i = 0
            while i < len(r):
                if r[i] in letters and (i == 0 or r[i - 1] not in letters):
                    j = i
                    while j < len(r) and r[j] in letters:
                        j += 1
                    w = r[i:j]
                    if 3 <= len(w) <= 14:
                        cnt[w] += 1
                        if i > 0 and r[i - 1] == sp:
                            cnt[bytes([sp]) + w] += 1
                        if j < len(r) and r[j] == sp:
                            cnt[w + bytes([sp])] += 1
                    i = j
                else:
                    i += 1
        best, gain = None, 0
        for w, k in cnt.items():
            g = k * (len(w) - 2) - (len(w) + 3)
            if g > gain:
                best, gain = w, g
        if not best:
            break
        words.append(best)
        runs = [r.replace(best, bytes([marker])) for r in runs]
        runs = [p for r in runs for p in r.split(bytes([marker])) if p]
    return words


def apply_dict(segs, words):
    """Sostituisce le parole del dizionario (le piu' lunghe prima) nei pezzi comprimibili: lista di pezzi
    (tipo, bytes) con tipo 'w' (riferimento 01 xx gia' pronto), True (testo comprimibile), False (fisso)."""
    order = sorted(range(len(words)), key=lambda k: -len(words[k]))
    out = []
    for f, b in segs:
        if not f:
            out.append((False, b)); continue
        parts = [(True, b)]
        for k in order:
            w = words[k]
            nxt = []
            for pf, pb in parts:
                if pf is not True or w not in pb:
                    nxt.append((pf, pb)); continue
                pieces = pb.split(w)
                for n, piece in enumerate(pieces):
                    if n:
                        nxt.append(("w", bytes([0x01, k])))
                    if piece:
                        nxt.append((True, piece))
            parts = nxt
        out += parts
    return out


def choose_dte(runs, n=C.N_DTE):
    """Digrammi: coppie piu' frequenti, scelte una alla volta (golose, senza sovrapposizioni)."""
    runs = [list(r) for r in runs]
    pairs = []
    for k in range(n):
        cnt = Counter()
        for r in runs:
            for a, b in zip(r, r[1:]):
                if a < 0x100 and b < 0x100:
                    cnt[(a, b)] += 1
        if not cnt:
            break
        (a, b), _ = cnt.most_common(1)[0]
        pairs.append((a, b))
        tok = 0x100 + k
        new = []
        for r in runs:
            o, i = [], 0
            while i < len(r):
                if i + 1 < len(r) and r[i] == a and r[i + 1] == b:
                    o.append(tok); i += 2
                else:
                    o.append(r[i]); i += 1
            new.append(o)
        runs = new
    return pairs


def apply_dte(b, pairs):
    """Codifica golosa sinistra->destra con i digrammi (stessa priorita' della scelta)."""
    prio = {p: k for k, p in enumerate(pairs)}
    r = list(b)
    for k, (a, c) in enumerate(pairs):
        o, i = [], 0
        while i < len(r):
            if i + 1 < len(r) and r[i] == a and r[i + 1] == c:
                o.append(0xB0 + k); i += 2
            else:
                o.append(r[i]); i += 1
        r = o
    return bytes(r)


# ------------------------------------------------------------------------------------------- grafica
def chr_tile(data, prg_size, bank, n):
    o = 16 + prg_size + bank * 4096 + n * 16
    return data[o:o + 16]


def set_tile(data, prg_size, bank, n, t):
    o = 16 + prg_size + bank * 4096 + n * 16
    data[o:o + 16] = t


# accenti: righe 0-3 della meta' alta (le minuscole cominciano alla riga 5)
GRAVE = {2: 0b00010000, 3: 0b00001000}
ACUTE = {2: 0b00001000, 3: 0b00010000}


def draw_accents(data, prg_size):
    base = {"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u"}
    for ch, b in base.items():
        code = C.SINGLE[ch]
        top = bytearray(chr_tile(data, prg_size, 60, C.SINGLE[b]))
        bot = bytearray(chr_tile(data, prg_size, 61, C.SINGLE[b]))
        planes = [p for p in (0, 1) if any(top[p * 8 + y] for y in range(8))] or [0]
        if ch == "ì":                                        # niente puntino
            for y in range(5):
                top[y] = top[y + 8] = 0
        for y, bits in (ACUTE if ch == "é" else GRAVE).items():
            for p in planes:
                top[p * 8 + y] |= bits
        set_tile(data, prg_size, 60, code, bytes(top))
        set_tile(data, prg_size, 61, code, bytes(bot))
    # È: E maiuscola accorciata (righe 3-11) + accento grave alle righe 0-1
    E = C.SINGLE["E"]
    rows = []
    for bank in (60, 61):
        t = chr_tile(data, prg_size, bank, E)
        rows += [(t[y], t[y + 8]) for y in range(8)]
    body = rows[1:12]                                         # E originale: righe 1-11
    keep = [body[0], body[2], body[4], body[5], body[7], body[8], body[9], body[10], body[10]]
    keep[-1] = body[10]
    new = [(0, 0)] * 16
    acc = [0b00010000, 0b00001000]
    p0 = 1 if any(r[0] for r in body) else 0
    for y, bits in enumerate(acc):
        new[y] = (bits, 0) if p0 else (0, bits)
    # E compressa: barra alta, 2 righe, barra media, 3 righe, barra bassa (= 9 righe, 3..11)
    top_bar, stem, mid_bar, bot_bar = body[0], body[1], body[5], body[10]
    for y, r in zip(range(3, 12), [top_bar, stem, stem, mid_bar, stem, stem, stem, stem, bot_bar]):
        new[y] = r
    for bank, part in ((60, new[:8]), (61, new[8:])):
        t = bytes([r[0] for r in part] + [r[1] for r in part])
        set_tile(data, prg_size, bank, C.SINGLE["È"], t)
    # À: A maiuscola accorciata (8 righe, 4..11) + accento grave alle righe 1-2
    rows = []
    for bank in (60, 61):
        t = chr_tile(data, prg_size, bank, C.SINGLE["A"])
        rows += [(t[y], t[y + 8]) for y in range(8)]
    body = rows[1:12]
    new = [(0, 0)] * 16
    p0 = 1 if any(r[0] for r in body) else 0
    for y, bits in ((1, 0b00010000), (2, 0b00001000)):
        new[y] = (bits, 0) if p0 else (0, bits)
    for y, r in zip(range(4, 12), [body[i] for i in (0, 2, 4, 6, 7, 8, 9, 10)]):
        new[y] = r
    for bank, part in ((60, new[:8]), (61, new[8:])):
        t = bytes([r[0] for r in part] + [r[1] for r in part])
        set_tile(data, prg_size, bank, C.SINGLE["À"], t)


def draw_dte(data, prg_size, pairs):
    for k, (a, b) in enumerate(pairs):
        n = (0xB0 + k - 0xAF) * 2
        for i, ch in enumerate((a, b)):
            set_tile(data, prg_size, 62, n + i, chr_tile(data, prg_size, 60, ch))
            set_tile(data, prg_size, 63, n + i, chr_tile(data, prg_size, 61, ch))


# ------------------------------------------------------------------------------------------- spazio
def free_regions(data):
    """Catene di spazio libero [(unita' iniziale, offset iniziale, unita' finale inclusa, offset finale)].
    Dentro una catena un messaggio puo' passare da un'unita' alla successiva (la finestra $A000 = unita'+1)."""
    prg = data[16:16 + 512 * 1024]
    def tail(u, margin=16):
        seg = prg[u * UNIT:(u + 1) * UNIT]
        t = len(seg)
        while t and seg[t - 1] == 0xFF:
            t -= 1
        t += margin
        return t + (t & 1)
    chains = [
        (8, tail(8, 0x40), 9, UNIT),          # coda dell'unita' 8 + unita' 9
        (15, 0, 27, UNIT),                    # 15-27 (testo inglese)
        (34, 0, 35, UNIT),
        (43, 0, 43, UNIT),                    # vuota nel gioco
        (47, 0, 47, 0x1000),                  # prima della tabella dei banchi
    ]
    for u in (28, 29, 30, 31, 40, 41, 42):    # code vuote (FF) di unita' di dati
        s = tail(u)
        if s < UNIT - 32:
            chains.append((u, s, u, UNIT))
    return chains


def layout(msgs, chains):
    """msgs: lista di bytes gia' terminati (00 00). Ritorna {i: (unita', indirizzo nella finestra)}."""
    pos = {}
    cur = [(u0 * UNIT + o0, u1 * UNIT + o1) for u0, o0, u1, o1 in chains]
    ptr = [a for a, _ in cur]
    for i, m in enumerate(msgs):
        for ci, (a, end) in enumerate(cur):
            p = ptr[ci] + (ptr[ci] & 1)
            if p + len(m) <= end:
                pos[i] = (p // UNIT, p % UNIT)
                ptr[ci] = p + len(m)
                break
        else:
            raise ValueError("spazio esaurito al messaggio %d" % i)
    used = sum(ptr[ci] - cur[ci][0] for ci in range(len(cur)))
    total = sum(e - a for a, e in cur)
    return pos, used, total


# ------------------------------------------------------------------------------------------ controlli
def check_width(idx, text):
    bad = []
    for line in re.split(r"<05>|<5E>|<00>", text):
        vis = re.sub(r"<[0-9A-F]{2}>[0-9!.]*|\{[0-9A-F]{2}:[0-9A-F]{2}\}", "", line)
        w = len(re.sub(r"\$(\d)", lambda m: "x" * VAR_W.get(m.group(1), 7), vis))
        if w > WIDTH:
            bad.append((w, line))
    return bad


# ---------------------------------------------------------------------------------------------- main
def main():
    src, it_tsv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    here = os.path.dirname(os.path.abspath(__file__))
    en_tsv = os.path.join(here, "..", "text", "en.tsv")
    data = bytearray(open(src, "rb").read())
    prg_size = data[4] * 16384
    prg = bytes(data[16:16 + prg_size])
    assert C.read_message(prg, 0) and data[16 + 62 * UNIT + 0xD0CF - 0xC000] == 0x20, "non e' la ROM inglese di Stealth"
    en, it = load_texts(en_tsv, it_tsv)
    texts = {k: it.get(k, en[k]) for k in range(0, 2 * C.N_MSG, 2)}
    print("messaggi tradotti: %d / %d" % (len(it), C.N_MSG))

    plains = {k: C.encode_plain(t) for k, t in texts.items()}
    for k, p in plains.items():
        assert b"\x00\x00" not in p and not p.endswith(b"\x00"), "messaggio %04X: 00 doppio o finale" % k
    segs = {k: segments(p) for k, p in plains.items()}
    words = choose_dict(list(segs.values()))
    parts = {k: apply_dict(s, words) for k, s in segs.items()}
    # digrammi: quelli della patch inglese, INVARIATI: li usano anche i nomi di personaggi e mostri (unita' 57, con
    # una copia della tabella a 57:$9E..), i crediti (unita' 37, tabella propria) e altri testi gia' in ROM.
    pairs = [(C.SINGLE[p[0]], C.SINGLE[p[1]]) for p in C.EN_DTE]
    print("dizionario: %d parole; digrammi: %d (inglesi)" % (len(words), len(pairs)))

    def enc(ps):
        return b"".join(apply_dte(b, pairs) if f is True else b for f, b in ps)
    msgs = [enc(parts[k]) + b"\x00\x00" for k in sorted(parts)]
    too_long = [(k, len(m)) for k, m in zip(sorted(parts), msgs) if len(m) > 256]
    assert not too_long, "messaggi oltre 256 byte: %s" % ", ".join("%04X (%d)" % x for x in too_long)
    wenc = [apply_dte(w, pairs) for w in words]

    # --- dizionario: puntatori a 46:1200, stringhe da 46:1400
    o = 46 * UNIT + 0x1400
    empty = None
    for i in range(256):
        if i < len(wenc):
            w = wenc[i] + b"\x00"
            data[16 + o:16 + o + len(w)] = w
            addr = 0x8000 + o - 46 * UNIT
            o += len(w)
        else:
            if empty is None:
                empty = 0x8000 + o - 46 * UNIT
                data[16 + o] = 0; o += 1
            addr = empty
        data[16 + C.DICT_OFF + 2 * i:16 + C.DICT_OFF + 2 * i + 2] = bytes([addr & 0xFF, addr >> 8])
    assert o <= 47 * UNIT, "dizionario troppo grande"
    data[16 + o:16 + 47 * UNIT] = b"\xFF" * (47 * UNIT - o)

    # --- messaggi
    chains = free_regions(data)
    for u0, o0, u1, o1 in chains:                       # pulisce le regioni (FF)
        a, b = 16 + u0 * UNIT + o0, 16 + u1 * UNIT + o1
        data[a:b] = b"\xFF" * (b - a)
    pos, used, total = layout(msgs, chains)
    print("testo: %d byte su %d disponibili (%.1f%%)" % (used, total, 100.0 * used / total))
    for n, k in enumerate(sorted(parts)):
        unit, off = pos[n]
        m = msgs[n]
        data[16 + unit * UNIT + off:16 + unit * UNIT + off + len(m)] = m
        data[16 + C.PTR_OFF + k] = (off >> 1) & 0xFF
        data[16 + C.PTR_OFF + k + 1] = (off >> 9) & 0x0F
        data[16 + C.BANKTAB_OFF + k] = (unit - 0x10) & 0xFF

    # --- grafica
    draw_accents(data, prg_size)

    open(out, "wb").write(data)
    print("scritta", out)

    # --- verifica: rilettura dalla ROM scritta
    prg2 = bytes(data[16:16 + prg_size])
    words2 = C.read_dict(prg2)
    dte_txt = ["".join(C.SINGLE_INV[x] for x in p) for p in pairs]
    bad = 0
    for k in sorted(parts):
        raw = C.read_message(prg2, k)
        if C.expand(raw, words2, dte_txt) != plains[k]:
            bad += 1
            if bad < 5:
                print("DIVERSO %04X" % k)
    print("verifica rilettura: %d messaggi, diversi: %d" % (len(parts), bad))
    try:
        from dialog_decode import Game
    except ImportError:
        Game = None
    if Game:
        g = Game(out)
        gbad = 0
        for k in sorted(parts):
            g.message(k)                           # la routine del gioco copia il messaggio in $6400
            e = 0x6400
            while not (g.mem[e] == 0 and g.mem[e + 1] == 0):
                e += 1
            if C.expand(bytes(g.mem[0x6400:e]), words2, dte_txt) != plains[k]:
                gbad += 1
        print("verifica con la routine del gioco (py65): diversi: %d" % gbad)
    over = [(k, b) for k in sorted(it) for b in check_width(k, it[k])]
    print("righe troppo lunghe nei messaggi tradotti: %d" % len(over))
    for k, (w, line) in over[:30]:
        print("  %04X (%d) %s" % (k, w, line))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
