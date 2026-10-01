"""Parole dei menu disegnate come grafica (banchi CHR 60 alto / 61 basso, codici A0-FF) per la base inglese.

Nella versione inglese comandi e stati sono tile pre-disegnati (es. B0-B4 = "Speak"), usati direttamente dalle
stringhe dei menu dell'unita' 58. Qui si ridisegnano con le parole italiane: font normale (glifi del font dei
dialoghi, rifilati e accostati con 1 pixel di spazio) se la parola ci sta, altrimenti font stretto (4 pixel).
"""
import charmap_en as C

# (primo codice, numero di tile, parole candidate in ordine di preferenza)
MENU_WORDS = [
    (0xA0, 4, ["Altro"]),          # Misc
    (0xA4, 3, ["Sosta"]),          # Hold
    (0xA7, 4, ["Lotta"]),          # Fight
    (0xAB, 4, ["Togli"]),          # Unarm
    (0xB0, 5, ["Parla"]),          # Speak
    (0xB5, 4, ["Magia"]),          # Magic
    (0xBA, 4, ["Zaino"]),          # Items
    (0xC0, 4, ["Equip"]),          # Equip
    (0xC4, 5, ["Stato"]),          # Status
    (0xC9, 5, ["Cerca"]),          # Search
    (0xD0, 4, ["Menu"]),           # Menu
    (0xD4, 4, ["Arma"]),           # Arms
    (0xD8, 4, ["Abito"]),          # Armor
    (0xDC, 4, ["Scudo"]),          # Shield
    (0xE6, 3, ["Tox"]),            # Poison
    (0xE9, 3, ["Sonno"]),          # Sleep
    (0xEC, 3, ["Malia"]),          # Charm
    (0xF0, 3, ["Shock"]),          # Stun
    (0xF3, 3, ["Sasso"]),          # Stone
    (0xF6, 3, ["Morto"]),          # Dead
]

# font stretto: righe 0-10 (le minuscole occupano 4-10), '3' = pixel
_N = {
    "S": [".33.", "3..3", "3..3", "3...", "3...", ".33.", "...3", "...3", "3..3", "3..3", ".33."],
    "M": ["3...3", "33.33", "3.3.3", "3.3.3", "3...3", "3...3", "3...3", "3...3", "3...3", "3...3", "3...3"],
    "T": ["33333", "..3..", "..3..", "..3..", "..3..", "..3..", "..3..", "..3..", "..3..", "..3..", "..3.."],
    "l": ["3"] * 11,
    "i": [".", ".", "3", ".", "3", "3", "3", "3", "3", "3", "3"],
    "h": ["3...", "3...", "3...", "3...", "3.3.", "33.3", "3..3", "3..3", "3..3", "3..3", "3..3"],
    "k": ["3...", "3...", "3...", "3...", "3..3", "3.3.", "33..", "3.3.", "3..3", "3..3", "3..3"],
    "d": ["...3", "...3", "...3", "...3", ".333", "3..3", "3..3", "3..3", "3..3", "3..3", ".333"],
    "t": [".", ".3.", ".3.", ".3.", "333", ".3.", ".3.", ".3.", ".3.", ".3.", "..3"],
    "L": ["3...", "3...", "3...", "3...", "3...", "3...", "3...", "3...", "3...", "3...", "3333"],
    "A": [".33.", "3..3", "3..3", "3..3", "3..3", "3333", "3..3", "3..3", "3..3", "3..3", "3..3"],
    "C": [".33.", "3..3", "3...", "3...", "3...", "3...", "3...", "3...", "3...", "3..3", ".33."],
    "E": ["3333", "3...", "3...", "3...", "3...", "333.", "3...", "3...", "3...", "3...", "3333"],
    "P": ["333.", "3..3", "3..3", "3..3", "333.", "3...", "3...", "3...", "3...", "3...", "3..."],
    "Z": ["3333", "...3", "...3", "..3.", "..3.", ".3..", ".3..", "3...", "3...", "3...", "3333"],
    "b": ["3...", "3...", "3...", "3...", "333.", "3..3", "3..3", "3..3", "3..3", "3..3", "333."],
}
_LOW = {   # minuscole alte 7 righe (4-10)
    "o": [".33.", "3..3", "3..3", "3..3", "3..3", "3..3", ".33."],
    "n": ["3.3.", "33.3", "3..3", "3..3", "3..3", "3..3", "3..3"],
    "a": [".33.", "...3", ".333", "3..3", "3..3", "3..3", ".333"],
    "c": [".33.", "3..3", "3...", "3...", "3...", "3..3", ".33."],
    "r": ["3.33", "33..", "3...", "3...", "3...", "3...", "3..."],
    "x": ["3..3", "3..3", ".33.", ".33.", ".33.", "3..3", "3..3"],
    "s": [".333", "3...", "3...", ".33.", "...3", "...3", "333."],
    "e": [".33.", "3..3", "3..3", "3333", "3...", "3..3", ".33."],
    "u": ["3..3", "3..3", "3..3", "3..3", "3..3", "3..3", ".333"],
    "g": [".333", "3..3", "3..3", "3..3", "3..3", ".333", "...3"],   # (coda tagliata: 7 righe)
    "m": ["33.3.", "3.3.3", "3.3.3", "3.3.3", "3.3.3", "3.3.3", "3.3.3"],
    "p": ["333.", "3..3", "3..3", "3..3", "333.", "3...", "3..."],
    "q": [".333", "3..3", "3..3", "3..3", ".333", "...3", "...3"],
}
for _c, _g in _LOW.items():
    _N[_c] = ["." * len(_g[0])] * 4 + _g


def _narrow(ch):
    g = _N[ch]
    w = max(len(r) for r in g)
    return [[1 if x < len(r) and r[x] == "3" else 0 for x in range(w)] + [0] * 0 for r in g] + [[0] * w] * (16 - len(g))


def _regular(data, prg_size, ch):
    """Glifo del font dei dialoghi (16 righe), rifilato alle colonne con inchiostro."""
    code = C.SINGLE[ch]
    rows = []
    for bank in (60, 61):
        o = 16 + prg_size + bank * 4096 + code * 16
        for y in range(8):
            v = data[o + y] | data[o + y + 8]
            rows.append([(v >> (7 - x)) & 1 for x in range(8)])
    cols = [x for x in range(8) if any(r[x] for r in rows)]
    if not cols:                                        # spazio
        return [[0] * 3 for _ in range(16)]
    return [r[cols[0]:cols[-1] + 1] for r in rows]


def _compose(glyphs):
    w = sum(len(g[0]) for g in glyphs) + len(glyphs) - 1
    img = [[0] * w for _ in range(16)]
    x = 0
    for g in glyphs:
        for y in range(16):
            for i, v in enumerate(g[y]):
                if v:
                    img[y][x + i] = 1
        x += len(g[0]) + 1
    return img


def render_word(data, prg_size, word, ntiles, kinds=("normale", "stretto")):
    """-> (immagine 16 x ntiles*8, font usato) o (None, None) se non entra."""
    for kind in kinds:
        try:
            gl = [(_regular(data, prg_size, c) if kind == "normale" else _narrow(c)) for c in word]
        except KeyError:
            continue
        img = _compose(gl)
        w = len(img[0])
        if w <= ntiles * 8:
            off = (ntiles * 8 - w) // 2
            full = [[0] * (ntiles * 8) for _ in range(16)]
            for y in range(16):
                full[y][off:off + w] = img[y]
            return full, kind
    return None, None


def draw_menu_words(data, prg_size):
    out = []
    for start, n, cands in MENU_WORDS:
        for word in cands:
            # gli stati (E6-F8) sempre col font stretto, come nell'inglese
            kinds = ("stretto",) if start >= 0xE6 else ("normale", "stretto")
            img, kind = render_word(data, prg_size, word, n, kinds)
            if img:
                break
        else:
            raise ValueError("nessuna parola entra in %d tile: %r" % (n, cands))
        for t in range(n):
            for half, bank in ((0, 60), (1, 61)):
                o = 16 + prg_size + bank * 4096 + (start + t) * 16
                for y in range(8):
                    bits = 0
                    for x in range(8):
                        bits = (bits << 1) | img[half * 8 + y][t * 8 + x]
                    data[o + y] = bits          # colore 3: entrambi i piani, come i tile inglesi
                    data[o + y + 8] = bits
        out.append("%s(%s)" % (word, kind[0]))
    return out
