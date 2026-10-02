#!/usr/bin/env python3
"""Unisce i semi raccolti giocando (--miss-log / miss.on: "4k:BB:AAAA conteggio") a cycle_seeds.txt.

  python tools/merge_seeds.py cycle_seeds.txt build/cycle_seeds_played.txt build_rom/jb_it.nes [rom_giocata.nes]

Se i semi vengono da un'altra ROM (rom_giocata), si tengono solo quelli i cui primi 3 byte sono identici
nella ROM corrente (stesso codice nello stesso banco): un indirizzo valido la' potrebbe non esserlo qui.
"""
import sys


def prg(path):
    d = open(path, "rb").read()
    return d[16:16 + d[4] * 16384]


def main():
    seeds_path, played_path, rom = sys.argv[1], sys.argv[2], prg(sys.argv[3])
    other = prg(sys.argv[4]) if len(sys.argv) > 4 else None
    lines = open(seeds_path, encoding="utf-8").read().splitlines()
    have = set(l.strip() for l in lines if l.startswith("4k:"))
    added = skipped = 0
    for l in open(played_path, encoding="utf-8"):
        if not l.startswith("4k:"):
            continue
        key = l.split()[0]
        if key in have:
            continue
        _, bank, addr = key.split(":")
        off = int(bank, 16) * 4096 + (int(addr, 16) & 0xFFF)
        if other is not None and rom[off:off + 3] != other[off:off + 3]:
            skipped += 1
            continue
        have.add(key)
        lines.append(key)
        added += 1
    open(seeds_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("semi aggiunti: %d, scartati (codice diverso nella ROM corrente): %d, totale: %d" % (added, skipped, len(have)))


if __name__ == "__main__":
    main()
