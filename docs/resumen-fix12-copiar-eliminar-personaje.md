# Kenshi Save Editor - fix12 copiar y eliminar personaje

Archivo generado: `KenshiSaveEditor-Fase2-fix12.exe`

## Nuevo

- Boton `Copiar personaje` debajo de la lista de escuadrones.
- Boton `Eliminar personaje` debajo de la lista de escuadrones.
- La copia se crea dentro del mismo `.platoon`, justo despues del grupo original.
- La copia recibe IDs nuevos para evitar colisiones.
- Las referencias internas entre personaje y records copiados se remapean.
- Si hay una instancia de posicion, se duplica cerca del personaje original con un pequeno desplazamiento.

## Seguridad

- Si hay estadisticas pendientes sin guardar, copiar/eliminar se bloquea para evitar mezclar operaciones.
- Copiar requiere encontrar la instancia de posicion del personaje; si no se encuentra, no copia a ciegas.
- Se respetan las opciones existentes:
  - `Backup`
  - `Guardar como copia`

## Verificacion

- Tests: `33 passed`
- Arranque desde codigo: correcto
- Ejecutable generado correctamente y verificado con `--smoke-test`
