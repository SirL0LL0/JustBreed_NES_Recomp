# JustBreedRecomp

Porting nativo per PC di Just Breed (NES), con una traduzione italiana completa applicata in fase di build
sopra la traduzione inglese di Stealth Translations. Gira sul **backend cycle-accurate di nesrecomp** (upstream, `runner/cyc`): ogni istruzione
della ROM e' ricompilata in C ciclo per ciclo su una macchina NES cycle-accurate (CPU, PPU, APU, MMC5 con
ExRAM, moltiplicatore, IRQ a scanline). Il codice non ancora incontrato gira sull'interprete della stessa
macchina (identico ciclo per ciclo, solo piu' lento): non e' un'emulazione approssimata.

Sopra c'e' il livello applicazione del fork (`nesrecomp/runner/cyc/app`, branch `cycle-app`): launcher
grafico, menu di gioco, mod (cheat), salvataggi di stato. Di questo repository restano solo l'identita' del
gioco (`game.c`), i cheat (`cheats.c`) e **tutto il lavoro di traduzione** (`text/`, `tools/`, `docs/`).

## Compilare e giocare

```
git clone --recurse-submodules <url di questo repo>
python tools/en_extract.py baserom.nes text/en.tsv
python tools/build_en_it.py baserom.nes text/it_en.tsv build_rom/jb_it.nes
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
build\JustBreedRecomp.exe                              # launcher (recomp-ui): scegli la ROM, Mod, Gioca
build\JustBreedRecomp.exe build_rom\jb_it.nes   # senza launcher
```

`baserom.nes` (Just Breed con la patch inglese di Stealth applicata) non e' incluso: procurati la tua copia
legale. Altre ROM (giapponese, inglese) partono lo stesso, solo sull'interprete. CMake cerca
`./nesrecomp` e `./recomp-ui` (submodule); in alternativa `-DNESRECOMP_ROOT=...` e `-DRECOMP_UI_ROOT=...`.
Serve Python 3.11+ (la generazione del codice avviene durante la configurazione).

Il riconoscimento della ROM (launcher e mod) non usa il CRC32 dell'intero file, perche' cambia a ogni build
della traduzione: usa il CRC32 del banco fisso 62, mai toccato dalla patch italiana (vedi `cheats.c`).

## Controlli, cheat, salvataggi di stato

Uguali a Castlevania3Recomp (stesso livello applicazione): Esc apre il menu di gioco (schermo, grafica, audio,
salva/carica stato), F1-F12 carica lo slot, Maiusc+F1-F12 salva lo slot (`savestates/`, accanto all'exe), Tab
avanti veloce, Ctrl+F11 overlay con le statistiche (nativo/interprete), Ctrl+F12 screenshot.

I cheat sono in `mods/packages/justbreed.cheats` (18 codici RAM: vite/PM/oro/esperienza dei 6 personaggi,
nemici senza salute) e si attivano dalla pagina **Mod** del launcher.

## Il lavoro di traduzione

| Cartella | Contenuto |
|----------|-----------|
| `text/` | **la traduzione.** `it_en.tsv` + `it_en/*.tsv` (dialoghi, id -> italiano), `it_en_ui.tsv` (oggetti, luoghi, menu, messaggi di battaglia), `intro_it_en.txt` (introduzione). `en.tsv`/`en_dict.tsv` (copione inglese estratto) restano solo in locale |
| `tools/` | pipeline di estrazione/costruzione/verifica (sotto) e il wrapper del disassemblatore |
| `docs/` | `script_codes.md` (i comandi inline del testo), `REVERSE_ENGINEERING.md` |
| `analysis/all.bin` (+ `.ram`/`.win`/`.wramw`) | copertura del codice, base del disassemblato |

```
tools/en_extract.py      estrae il copione inglese (dialoghi non compressi, digrammi, dizionario) -> text/en.tsv
tools/build_en_it.py     costruisce la ROM: dialoghi (dizionario ricalcolato), testi fissi, intro, accenti,
                         parole dei menu (tools/menu_words.py), verifica con la routine del gioco (py65)
tools/rewrap_en.py       impagina le pagine troppo larghe (--force/--merge per riflusso e unione pagine)
tools/en_missing.py      elenca i messaggi con testo non ancora tradotti
tools/preview_en.py      disegna un messaggio coi tile veri della ROM costruita
tools/merge_seeds.py     unisce i semi raccolti giocando a cycle_seeds.txt
tools/disasm.py          disassemblatore (strumento del vecchio backend, vedi l'intestazione)
```

## Copertura del codice nativo (opzionale)

`cycle_seeds.txt` elenca gli indirizzi da compilare in codice nativo (18379, dalla vecchia copertura). Il
resto funziona lo stesso, sull'interprete, solo piu' lento. Per ampliarla giocando: crea un file vuoto
`miss.on` accanto all'exe; all'uscita scrive `cycle_seeds_played.txt` (si accumula tra le sessioni).
