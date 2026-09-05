# Kenshi Save Editor

Un editor de partidas guardadas para [Kenshi](https://store.steampowered.com/app/233860/Kenshi/), con interfaz gráfica de escritorio. Te deja abrir una partida, ver tus escuadrones y personajes, y editar sus estadísticas — sin tocar nada a mano en binario.

El proyecto **lee el formato binario propietario de Kenshi (OCS/FCS) sin usar offsets hexadecimales hardcodeados**: en lugar de "el dato está en la posición X", interpreta la estructura real de los records, así que no se rompe si las posiciones cambian entre partidas.

> Herramienta no oficial hecha por un fan. No está afiliada ni respaldada por Lo-Fi Games, los creadores de Kenshi. Haz siempre copia de seguridad de tus partidas (de hecho, la herramienta la hace por ti antes de escribir).

## Qué hace

- Seleccionas una carpeta de partida guardada y valida que sea correcta (`quick.save`, `platoon/`, `zone/`).
- Analiza los archivos y **extrae escuadrones y personajes**: nombre, raza, sexo, escuadrón, estado e ID interno.
- Localiza los records `STATS` enlazados a cada personaje y te permite **editar sus estadísticas** por nombre de propiedad.
- **Backup automático** de la carpeta de save antes de escribir cualquier cambio.
- Puede guardar los cambios como copia, sin sobreescribir tu partida original.

## Funcionamiento

El proyecto separa la lógica del formato (`core/`) de la interfaz (`gui/`), de modo que el parser del formato está aislado y se puede sustituir sin tocar la GUI:

- `core/` — parseo del formato OCS/FCS, lectura binaria, extracción de personajes, servicios de stats y backup.
- `gui/` — interfaz de escritorio hecha con PySide6 (Qt).
- `tests/` — tests unitarios con pytest sobre el parser y los servicios.

Una decisión de diseño a propósito: si una estadística no aparece como campo estructurado en el record, se muestra como "no encontrada" en vez de inventársela. Nada de escribir a ciegas en el binario.

## Instalar y ejecutar

Requiere Python 3.12+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -e .[dev]
# Ejecutar:
.venv\Scripts\python -m kenshi_save_editor
```

En Windows también tienes los `.bat` de conveniencia (`run_fase2.bat`).

## Tests

```bash
.venv\Scripts\python -m pytest -q
```

## Estado

Versión estable. Lee y edita estadísticas de personajes con backup automático antes de escribir. Una función experimental de copiar/eliminar personajes dentro de un escuadrón está en desarrollo aparte, todavía sin integrar (porque no me funciona y rompe con la partida) asi que no se si subirla.

## Licencia

MIT — ver [LICENSE](LICENSE). Aplica al código de esta herramienta; Kenshi y su formato de datos son propiedad de Lo-Fi Games.
