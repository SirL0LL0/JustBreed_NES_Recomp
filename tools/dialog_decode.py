#!/usr/bin/env python3
"""Decodifica i messaggi (dialoghi) compressi di Just Breed eseguendo la routine originale del gioco
($D094 nel banco 62) con l'emulatore 6502 py65 (pip install py65).

Usato da build_en_it.py per verificare che la routine del gioco (banco 62) carichi ogni messaggio
come previsto. Nella base inglese la routine copia il testo non compresso (vedi charmap_en.py).

Il messaggio N (indice = offset in byte nella tabella dei puntatori a $8200 del banco 46) viene decompresso
in $6400 dal codice del gioco stesso: albero di Huffman a $8000 (banco 46), flusso di bit MSB-first,
blob nei banchi 16+.  Simboli: 01 kk = kanji, 02/03/04/60-63 pp = comando con parametro.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py65.devices.mpu6502 import MPU

UNIT = 8192


class Game:
    def __init__(self, rom_path):
        d = open(rom_path, "rb").read()
        self.prg = d[16:16 + d[4] * 16384]
        self.mpu = MPU()
        self.mem = self.mpu.memory = bytearray(0x10000)
        self.win = [None, None]
        self.load(0xC000, 62)          # finestra $C000: banco 62 (contiene il caricatore a $D094)
        self.load(0xE000, 63)          # finestra $E000: banco 63 (fisso)
        self.map(0, 0x6E)
        self.map(1, 0x6F)

    def load(self, addr, unit):
        self.mem[addr:addr + UNIT] = self.prg[unit * UNIT:(unit + 1) * UNIT]

    def map(self, w, bank):
        unit = bank & 0x3F
        self.win[w] = unit
        self.load(0x8000 + w * UNIT, unit)

    def call(self, addr, x=0, y=0, a=0, max_steps=400000):
        m = self.mpu
        # JSR fittizio: ritorno a $FFF0 (indirizzo sentinella)
        ret = 0xFFF0 - 1
        self.mem[0x1FF] = ret >> 8
        self.mem[0x1FE] = ret & 0xFF
        m.sp = 0xFD
        m.pc, m.x, m.y, m.a = addr, x, y, a
        steps = 0
        while m.pc != 0xFFF0:
            if m.pc == 0xC184:      # cambio banco finestra $8000
                self.map(0, m.a); self.mem[0xBC] = m.a; self._rts()
            elif m.pc == 0xC193:    # cambio banco finestra $A000
                self.map(1, m.a); self.mem[0xBD] = m.a; self._rts()
            else:
                m.step()
            steps += 1
            if steps > max_steps:
                raise RuntimeError("troppi passi")

    def _rts(self):
        m = self.mpu
        m.sp = (m.sp + 1) & 0xFF; lo = self.mem[0x100 + m.sp]
        m.sp = (m.sp + 1) & 0xFF; hi = self.mem[0x100 + m.sp]
        m.pc = ((hi << 8) | lo) + 1

    def message(self, index):
        self.mem[0x6400:0x6500] = bytes(256)
        self.call(0xD094, x=index & 0xFF, y=index >> 8)
        out = bytearray()
        for i in range(0x6400, 0x6400 + 0x400):
            if self.mem[i] == 0:
                break
            out.append(self.mem[i])
        return bytes(out)
