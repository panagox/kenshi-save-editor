# Kenshi Save Editor - fix11 cambios pendientes y copias

Archivo generado: `KenshiSaveEditor-Fase2-fix11.exe`

## Cambios de interfaz

- Cuando modificas una estadistica, el campo cambia de color.
- El cambio queda pendiente aunque cambies de personaje o escuadron.
- El boton muestra cuantos cambios pendientes hay: `Guardar estadisticas (N)`.
- Las columnas de las tablas son redimensionables.
- En la pestana de estadisticas hay un divisor vertical para ajustar el espacio entre stats y candidatos.

## Guardado

- `Backup` activado: modifica la partida actual y crea backup antes.
- `Backup` desactivado: modifica la partida actual sin backup.
- `Guardar como copia`: crea una carpeta nueva junto a la partida original y escribe ahi los cambios. La partida original no se toca.

## Verificacion

- Tests: `30 passed`
- Arranque desde codigo: correcto
- Arranque del `.exe` con `--smoke-test`: correcto
