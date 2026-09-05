from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if "--smoke-test" in sys.argv:
        import kenshi_save_editor.core.ocs_parser  # noqa: F401
        import kenshi_save_editor.core.ocs_writer  # noqa: F401

        return 0
    if "--diagnose-save" in sys.argv:
        from kenshi_save_editor.core.diagnostics import write_save_diagnostic

        save_index = sys.argv.index("--diagnose-save") + 1
        output_index = sys.argv.index("--diagnose-output") + 1
        name = None
        if "--diagnose-character" in sys.argv:
            name = sys.argv[sys.argv.index("--diagnose-character") + 1]
        platoon_file = None
        if "--diagnose-file" in sys.argv:
            platoon_file = Path(sys.argv[sys.argv.index("--diagnose-file") + 1])
        write_save_diagnostic(
            save_folder=Path(sys.argv[save_index]),
            output_path=Path(sys.argv[output_index]),
            character_name=name,
            platoon_file=platoon_file,
        )
        return 0
    from kenshi_save_editor.gui.app import run_app

    return run_app(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
