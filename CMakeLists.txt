cmake_minimum_required(VERSION 3.20)
project(JustBreedRecomp C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# nesrecomp (ramo cycle-app): submodule in ./nesrecomp, oppure -DNESRECOMP_ROOT=<percorso>
if(NOT NESRECOMP_ROOT)
    if(EXISTS ${CMAKE_SOURCE_DIR}/nesrecomp/runner/cyc/project.cmake)
        set(NESRECOMP_ROOT ${CMAKE_SOURCE_DIR}/nesrecomp)
    else()
        message(FATAL_ERROR "nesrecomp non trovato: git submodule update --init, oppure -DNESRECOMP_ROOT=<percorso>")
    endif()
endif()
message(STATUS "nesrecomp: ${NESRECOMP_ROOT}")

# recomp-ui (launcher e menu di gioco): submodule ./recomp-ui, oppure -DRECOMP_UI_ROOT=<percorso>
if(NOT RECOMP_UI_ROOT)
    if(EXISTS ${CMAKE_SOURCE_DIR}/recomp-ui/recomp_ui.cmake)
        set(RECOMP_UI_ROOT ${CMAKE_SOURCE_DIR}/recomp-ui)
    else()
        message(FATAL_ERROR "recomp-ui non trovato: git submodule update --init, oppure -DRECOMP_UI_ROOT=<percorso>")
    endif()
endif()
message(STATUS "recomp-ui: ${RECOMP_UI_ROOT}")

# Backend a cicli di nesrecomp: la ROM (la build italiana, generata da tools/build_en_it.py sopra la traduzione
# inglese di Stealth) viene ricompilata in C ciclo per ciclo; il codice non ancora visto gira sull'interprete.
# cycle_seeds.txt elenca gli indirizzi da compilare. Un'altra ROM (inglese, giapponese) gira solo sull'interprete.
include(${NESRECOMP_ROOT}/runner/cyc/project.cmake)
include(${NESRECOMP_ROOT}/runner/cyc/app/app.cmake)

set(JB_ROM "${CMAKE_SOURCE_DIR}/build_rom/jb_it.nes" CACHE FILEPATH
    "ROM di Just Breed tradotta (tools/build_en_it.py baserom.nes text/it_en.tsv <qui>)" FORCE)
nesrecomp_add_cycle_game(JustBreedRecomp
    ROM ${JB_ROM}
    SEED_FILE ${CMAKE_SOURCE_DIR}/cycle_seeds.txt
    HEADLESS)                       # niente cyc_sdl.c: l'host interattivo e' cyc_app.c
nesrecomp_cyc_app(JustBreedRecomp)
target_sources(JustBreedRecomp PRIVATE game.c cheats.c)
target_include_directories(JustBreedRecomp PRIVATE ${CMAKE_SOURCE_DIR})

set(RECOMP_UI_ENABLE_MODS ON CACHE BOOL "" FORCE)
include(${RECOMP_UI_ROOT}/recomp_ui.cmake)
recomp_target_launcher_ui(JustBreedRecomp CONSOLE nes LANGUAGE it)
recomp_target_runtime_ui_sdlrenderer2(JustBreedRecomp)

# Pacchetti mod (cheat) accanto all'eseguibile: mods/packages/<id>/<versione>/manifest.toml
add_custom_command(TARGET JustBreedRecomp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/mods/packages"
        "$<TARGET_FILE_DIR:JustBreedRecomp>/mods/packages")

if(WIN32)
    target_link_libraries(JustBreedRecomp PRIVATE ws2_32)
endif()
