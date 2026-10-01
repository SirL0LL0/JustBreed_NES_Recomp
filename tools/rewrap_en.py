#!/usr/bin/env python3
"""Ri-impagina le pagine di testo che superano la larghezza del riquadro (22 colonne).

  python tools/rewrap_en.py text/it_en/04.tsv [...]      # modifica i file sul posto, stampa cosa cambia

Una "pagina" e' una serie di righe separate da <05> senza altri comandi in mezzo (<5E>, <23>... la chiudono).
Solo le pagine con almeno una riga troppo lunga vengono riunite e rispezzate parola per parola (lo spazio
iniziale della prima riga, usato dopo <5E>, resta). Le righe gia' corte e le pagine con comandi non si toccano.
"""
import re, sys

WIDTH = 22
VAR_W = {"0": 7, "1": 6, "2": 7}
CMD = re.compile(r"<(?!05>)[0-9A-F]{2}>[0-9!. ]*?(?=<|$)|\{[0-9A-F]{2}:[0-9A-F]{2}\}")


def width(s):
    return len(re.sub(r"\$(\d)", lambda m: "x" * VAR_W.get(m.group(1), 7), s))


def wrap(words, first_indent):
    lines, cur = [], first_indent
    for w in words:
        cand = (cur + " " + w) if cur.strip() else (cur + w)
        if width(cand) <= WIDTH or not cur.strip():
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fix_page(page):
    lines = page.split("<05>")
    if all(width(l) <= WIDTH for l in lines):
        return page
    lead = re.match(r" *", lines[0]).group(0)
    words = " ".join(l.strip() for l in lines).split()
    return "<05>".join(wrap(words, lead))


def fix_text(t):
    # separa i comandi (non <05>) e <5E>: le pagine sono i pezzi di testo tra un comando e l'altro
    parts = re.split(r"(<5E>|<(?!05>)[0-9A-F]{2}>[0-9!. ]*|\{[0-9A-F]{2}:[0-9A-F]{2}\})", t)
    out = []
    for p in parts:
        if not p or p.startswith("<") and not p.startswith("<05>") or p.startswith("{"):
            out.append(p)
            continue
        # p puo' iniziare/finire con <05> (bordi della pagina): li conserva
        m = re.match(r"^((?:<05>)*)(.*?)((?:<05>)*)$", p, re.S)
        head, body, tail = m.groups()
        out.append(head + (fix_page(body) if body else body) + tail)
    return "".join(out)


def main():
    for path in sys.argv[1:]:
        src = open(path, encoding="utf-8").read().split("\n")
        changed = 0
        for i, l in enumerate(src):
            if "\t" not in l or l.startswith("#"):
                continue
            k, v = l.split("\t", 1)
            nv = fix_text(v)
            if nv != v:
                src[i] = k + "\t" + nv
                changed += 1
                print("%s %s\n   %s" % (path, k, nv))
        open(path, "w", encoding="utf-8", newline="\n").write("\n".join(src))
        print("%s: %d messaggi ri-impaginati" % (path, changed))


if __name__ == "__main__":
    main()
