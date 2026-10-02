"""Wrapper del disassemblatore MMC5 (tools/mmc5/disasm.py del vecchio backend di nesrecomp, branch mmc5-support).

Il nesrecomp attuale (branch cycle-app) non lo contiene: si usa una copia a parte, accanto a questo repository:
  git clone -b mmc5-support --depth 1 https://github.com/SirL0LL0/nesrecomp.git ../nesrecomp_tools
Copertura: analysis/all.bin (tools/seeds_to_coverage.py la aggiorna dai semi giocati).
"""
import os, sys, runpy, importlib.util
_here = os.path.dirname(os.path.abspath(__file__))
for _base in (os.path.join(_here, "..", "nesrecomp"), os.path.join(_here, "..", "..", "nesrecomp_tools")):
    _p = os.path.join(_base, "tools", "mmc5", "disasm.py")
    if os.path.exists(_p):
        break
else:
    sys.exit("disasm.py non trovato: clona il branch mmc5-support in ../nesrecomp_tools (vedi l'intestazione)")
_d = os.path.dirname(_p)
if _d not in sys.path:
    sys.path.insert(0, _d)
if __name__ == "__main__":
    runpy.run_path(_p, run_name="__main__")
else:
    _spec = importlib.util.spec_from_file_location("_mmc5_disasm", _p)
    _m = importlib.util.module_from_spec(_spec)
    sys.modules["_mmc5_disasm"] = _m
    _spec.loader.exec_module(_m)
    globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
