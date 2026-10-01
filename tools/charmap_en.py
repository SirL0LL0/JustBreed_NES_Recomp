"""Codifica del testo sulla base della traduzione inglese di Stealth (baserom.nes) di Just Breed.

La patch inglese NON usa piu' la compressione Huffman dei dialoghi: u62:$D0CF/$D0F3 (e $FEB6 nel banco fisso)
copiano il messaggio cosi' com'e' in $6400. Formato:
* puntatore: unita' 46 +0x200, indice = 2*n: lo, hi -> indirizzo $8000 | (hi&0F)<<9 | lo<<1 (pari);
* banco: unita' 47 +0x1000, byte all'indice 2*n: unita' = (valore + 0xD0) & 0x3F; la finestra $A000 riceve
  l'unita' successiva, quindi un messaggio puo' continuare nell'unita' dopo; il gioco ne copia 256 byte;
* fine messaggio: 00 00 (uno 00 singolo separa le parti di un messaggio).
Stampa dei caratteri (u58:$9E2A -> JMP $FEE0, banco fisso 63):
    01 xx   -> parola del dizionario xx: puntatori a 16 bit in unita' 46 +0x1200 ($9200, banco $EE),
               stringa terminata da 00, stampata ricorsivamente (puo' contenere digrammi, non altre parole);
    B0..FE  -> digramma: due celle 8x16, tile (c-0xAF)*2 e +1 dei banchi CHR 4KB 62 (sopra) / 63 (sotto);
    altri   -> carattere singolo, tile c dei banchi CHR 60 / 61.
Comandi del motore di stampa (u58:$9E13, tabella $9E3A): 1F 23 24 25 26 2A 2B 2D 2E 2F 3B 3E 40-44 46 49 5E;
05 = a capo; 02/03/04 xx = prefissi (kanji nel giapponese). Nel testo leggibile i comandi sono <xx>, tranne
$N (24 3N = variabile). Il punto e' 0x1E (0x2E e' un comando).
"""

UNIT = 8192
N_MSG = 2000
PTR_OFF = 46 * UNIT + 0x200
DICT_OFF = 46 * UNIT + 0x1200
BANKTAB_OFF = 47 * UNIT + 0x1000

CMD_BYTES = {0x1F, 0x23, 0x24, 0x25, 0x26, 0x2A, 0x2B, 0x2D, 0x2E, 0x2F, 0x3B, 0x3E,
             0x40, 0x41, 0x42, 0x43, 0x44, 0x46, 0x49, 0x5E}
CMD2 = (0x02, 0x03, 0x04)                                # prefisso + 1 byte

# carattere singolo -> codice
SINGLE = {}
for _i in range(26):
    SINGLE[chr(0x41 + _i)] = 0x61 + _i
    SINGLE[chr(0x61 + _i)] = 0x81 + _i
for _c in " !\"',0123456789:?":
    SINGLE[_c] = ord(_c)
SINGLE["."] = 0x1E
SINGLE["-"] = 0x28            # trattino ("top-class")
SINGLE["*"] = 0x29            # asterisco ("*sob*")
# lettere accentate (italiano): codici 06-0C, glifi kana inutilizzati dalla versione inglese (disegnati da build_en_it)
ACCENTED = "àèéìòùÈÀ"
for _i, _c in enumerate(ACCENTED):
    SINGLE[_c] = 0x06 + _i
SINGLE_INV = {v: k for k, v in SINGLE.items()}

# caratteri che possono stare in digrammi e parole del dizionario (mai argomenti di comandi)
COMPRESSIBLE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' ,." + ACCENTED)

# digrammi della patch inglese (riconosciuti dai tile CHR 62/63, tutti con corrispondenza esatta)
EN_DTE = ("ah in ar an or ea ir er ur on ed as it ll il li to is no en re st io os be lo us we at ly ae qu ac 't tt "
          "ss ai el le pp es ic me 'l mo ma by 'v 'r 's th ie em ig ec of un ti ie al ul uc In ot ol ho 'm if he ha "
          "se go so ou do ve oo ut ke").split()
N_DTE = 0xFF - 0xB0
assert len(EN_DTE) == N_DTE


def read_message(prg, idx):
    """Byte grezzi del messaggio idx (offset nella tabella), senza il terminatore 00 00."""
    lo, hi = prg[PTR_OFF + idx], prg[PTR_OFF + idx + 1]
    addr = ((hi & 0x0F) << 9) | (lo << 1)
    unit = (prg[BANKTAB_OFF + idx] + 0xD0) & 0x3F
    o = e = unit * UNIT + addr
    while not (prg[e] == 0 and prg[e + 1] == 0):
        e += 1
    return bytes(prg[o:e])


def read_dict(prg, n=256):
    words = []
    for i in range(n):
        p = prg[DICT_OFF + 2 * i] | prg[DICT_OFF + 2 * i + 1] << 8
        o = 46 * UNIT + p - 0x8000
        words.append(bytes(prg[o:prg.index(b"\x00", o)]))
    return words


def expand(raw, words, dte):
    """Espande parole del dizionario e digrammi: byte 'piani' (solo codici di carattere singolo e comandi)."""
    out, i = bytearray(), 0
    while i < len(raw):
        c = raw[i]
        if c == 0x01:
            out += expand(words[raw[i + 1]], words, dte); i += 2; continue
        if c in CMD2:
            out += raw[i:i + 2]; i += 2; continue
        if c >= 0xB0 and c != 0xFF:
            out += bytes(SINGLE[ch] for ch in dte[c - 0xB0])
        else:
            out.append(c)
        i += 1
    return bytes(out)


def render_plain(raw):
    """Byte piani -> testo leggibile (<xx> per comandi e codici sconosciuti, $N per le variabili)."""
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c in CMD2 and i + 1 < len(raw):
            out.append("{%02X:%02X}" % (c, raw[i + 1])); i += 2; continue
        if c == 0x24 and i + 1 < len(raw) and 0x30 <= raw[i + 1] <= 0x39:
            out.append("$" + chr(raw[i + 1])); i += 2; continue
        out.append(SINGLE_INV[c] if c in SINGLE_INV and c not in CMD_BYTES else "<%02X>" % c)
        i += 1
    return "".join(out)


def render(raw, words=None, dte=EN_DTE):
    return render_plain(expand(raw, words or [], dte))


def encode_plain(s):
    """Testo leggibile -> byte piani. Token: <xx>, {cc:pp}, $N."""
    import re
    tok = re.compile(r"<([0-9A-F]{2})>|\{([0-9A-F]{2}):([0-9A-F]{2})\}|\$([0-9])")
    out, i = bytearray(), 0
    while i < len(s):
        m = tok.match(s, i)
        if m:
            if m.group(1):
                out.append(int(m.group(1), 16))
            elif m.group(2):
                out += bytes([int(m.group(2), 16), int(m.group(3), 16)])
            else:
                out += bytes([0x24, 0x30 + int(m.group(4))])
            i = m.end()
            continue
        c = s[i]
        if c not in SINGLE:
            raise ValueError("carattere non disponibile %r in %r" % (c, s[:80]))
        out.append(SINGLE[c])
        i += 1
    return bytes(out)
