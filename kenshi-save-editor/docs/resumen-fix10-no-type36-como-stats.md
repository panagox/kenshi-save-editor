# Kenshi Save Editor - fix10 sin type 36 como stats

Archivo generado: `KenshiSaveEditor-Fase2-fix10.exe`

## Que corrige respecto a fix9

- Fix9 podia tratar un `GAMESTATE_CHARACTER` (`type 36`) como si fuera el bloque de estadisticas.
- Eso provocaba fuentes como `type 36`, `nombre '0'` y campos basura como `psts`, `ssct`, `age`, `decay`, etc.
- Fix10 solo muestra campos numericos extra cuando el bloque es `STATS` real (`type 25`).

## Que se mantiene

- Se mantiene la asignacion por nombre visible del personaje.
- Es decir: si en la lista eliges `Balls`, debe priorizar un `STATS` llamado `Balls`; si eliges `Kang`, uno llamado `Kang`.
- Se mantienen alias simples para campos internos como `combat`, `defence`, `unarmed`, `bow` y `tough`, pero solo dentro de `type 25`.

## Verificacion

- Tests: `28 passed`
- Arranque desde codigo: correcto
- Arranque del `.exe` con `--smoke-test`: correcto
