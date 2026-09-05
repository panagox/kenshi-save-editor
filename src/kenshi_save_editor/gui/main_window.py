from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kenshi_save_editor.core.character_extractor import extract_characters
from kenshi_save_editor.core.identity_service import all_numeric_fields, build_character_identity, record_label
from kenshi_save_editor.core.models import CharacterSummary, SaveAnalysis
from kenshi_save_editor.core.save_writer_service import save_modified_files, save_modified_files_to_copy
from kenshi_save_editor.core.save_scanner import SaveFolderError, analyze_save_folder
from kenshi_save_editor.core.stats_service import (
    CharacterStats,
    StatBinding,
    StatsCandidate,
    build_character_stats_from_record,
    find_character_stats,
    find_stats_candidates,
    set_stat_value,
)
from kenshi_save_editor.core.typecodes import type_name
from kenshi_save_editor.gui.styles import APP_STYLESHEET


StatKey = tuple[Path, int, int, str, str, str]


@dataclass(frozen=True)
class PendingStatChange:
    key: StatKey
    source_file: Path
    record_label: str
    stat_name: str
    field_kind: str
    field_key: str
    original_value: float
    value: float


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kenshi Save Editor - Fase 2 Stats")
        self.setStyleSheet(APP_STYLESHEET)
        self._analysis: SaveAnalysis | None = None
        self._characters: list[CharacterSummary] = []
        self._current_folder: Path | None = None
        self._current_stats: CharacterStats | None = None
        self._current_character: CharacterSummary | None = None
        self._stats_candidates: list[StatsCandidate] = []
        self._stats_order_offsets: dict[Path, int] = {}
        self._stat_widgets: list[tuple[StatBinding, QDoubleSpinBox]] = []
        self._modified_paths: set[Path] = set()
        self._pending_stat_changes: dict[StatKey, PendingStatChange] = {}
        self._stat_original_values: dict[StatKey, float] = {}

        self._summary_label = QLabel("Selecciona una carpeta de save de Kenshi.")
        self._tree_filter = QLineEdit()
        self._tree_filter.setPlaceholderText("Buscar escuadron o personaje")
        self._tree_filter.textChanged.connect(self._filter_tree)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Escuadron / Personaje", "Estado", "ID interno"])
        self._tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._tree.itemSelectionChanged.connect(self._show_selected_character)

        self._details = QTableWidget(0, 2)
        self._details.setHorizontalHeaderLabels(["Campo", "Valor"])
        self._details.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._details.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._details.verticalHeader().setVisible(False)

        self._identity_table = QTableWidget(0, 4)
        self._identity_table.setHorizontalHeaderLabels(["Tipo", "ID", "Razon", "Numericos"])
        self._identity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._identity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._identity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._identity_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._identity_table.verticalHeader().setVisible(False)

        self._instances_table = QTableWidget(0, 4)
        self._instances_table.setHorizontalHeaderLabels(["Instance ID", "Target", "Position", "States"])
        self._instances_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._instances_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._instances_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._instances_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._instances_table.verticalHeader().setVisible(False)

        self._stats_info = QLabel("Selecciona un personaje para ver estadisticas.")
        self._stats_table = QTableWidget(0, 4)
        self._stats_table.setHorizontalHeaderLabels(["Stat", "Valor", "Campo detectado", "Tipo"])
        self._stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._stats_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.verticalHeader().setVisible(False)

        self._candidates_table = QTableWidget(0, 5)
        self._candidates_table.setHorizontalHeaderLabels(["Fuente", "ID", "Razon", "Stats", "Vista previa"])
        self._candidates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._candidates_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._candidates_table.verticalHeader().setVisible(False)

        self._use_candidate_button = QPushButton("Usar bloque seleccionado")
        self._use_candidate_button.clicked.connect(self._use_selected_candidate)
        self._use_candidate_button.setEnabled(False)

        self._stats_offset_spinbox = QSpinBox()
        self._stats_offset_spinbox.setRange(-50, 50)
        self._stats_offset_spinbox.setValue(0)
        self._stats_offset_spinbox.valueChanged.connect(self._stats_offset_changed)

        self._save_stats_button = QPushButton("Guardar estadisticas")
        self._save_stats_button.clicked.connect(self._save_current_stats)
        self._save_stats_button.setEnabled(False)

        self._backup_checkbox = QCheckBox("Backup")
        self._backup_checkbox.setChecked(True)
        self._copy_checkbox = QCheckBox("Guardar como copia")

        self._files_table = QTableWidget(0, 4)
        self._files_table.setHorizontalHeaderLabels(["Archivo", "Records", "Tail bytes", "Tipos"])
        self._files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._files_table.verticalHeader().setVisible(False)

        for table in (
            self._details,
            self._identity_table,
            self._instances_table,
            self._stats_table,
            self._candidates_table,
            self._files_table,
        ):
            self._make_table_resizable(table)

        self._build_toolbar()
        self.setCentralWidget(self._build_content())
        self.statusBar().showMessage("Fase 2: edicion de stats con backup automatico.")

    def open_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta save",
            str(Path.home() / "AppData" / "Local" / "kenshi" / "save"),
        )
        if folder:
            self.open_save_folder(Path(folder))

    def open_save_folder(self, folder: Path) -> None:
        try:
            analysis = analyze_save_folder(folder)
        except SaveFolderError as exc:
            QMessageBox.warning(self, "Carpeta no valida", str(exc))
            return

        self._analysis = analysis
        self._current_folder = folder
        self._modified_paths.clear()
        self._pending_stat_changes.clear()
        self._stat_original_values.clear()
        self._characters, marker_found = extract_characters(analysis)
        self._populate_tree()
        self._populate_files()
        self._clear_stats()
        self._set_summary(marker_found)

    def refresh(self) -> None:
        if self._current_folder is not None:
            self.open_save_folder(self._current_folder)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Acciones")
        toolbar.setMovable(False)

        open_button = QPushButton("Abrir save")
        open_button.clicked.connect(self.open_dialog)
        toolbar.addWidget(open_button)

        refresh_button = QPushButton("Reanalizar")
        refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_button)

        self.addToolBar(toolbar)

    def _build_content(self) -> QWidget:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(self._summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Escuadrones"))
        left_layout.addWidget(self._tree_filter)
        left_layout.addWidget(self._tree)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        tabs = QTabWidget()

        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.addWidget(self._details)

        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.addWidget(self._stats_info)
        stats_splitter = QSplitter(Qt.Orientation.Vertical)
        stats_splitter.addWidget(self._stats_table)
        candidates_panel = QWidget()
        candidates_layout = QVBoxLayout(candidates_panel)
        candidates_layout.setContentsMargins(0, 0, 0, 0)
        candidates_layout.addWidget(QLabel("Bloques STATS candidatos del escuadron"))
        candidates_layout.addWidget(self._candidates_table)
        stats_splitter.addWidget(candidates_panel)
        stats_splitter.setSizes([320, 240])
        stats_layout.addWidget(stats_splitter, 1)
        stats_actions = QHBoxLayout()
        stats_actions.addWidget(self._use_candidate_button)
        stats_actions.addWidget(QLabel("Desplazamiento stats"))
        stats_actions.addWidget(self._stats_offset_spinbox)
        stats_actions.addWidget(self._backup_checkbox)
        stats_actions.addWidget(self._copy_checkbox)
        stats_actions.addStretch(1)
        stats_actions.addWidget(self._save_stats_button)
        stats_layout.addLayout(stats_actions)

        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)
        files_layout.addWidget(self._files_table)

        identity_tab = QWidget()
        identity_layout = QVBoxLayout(identity_tab)
        identity_layout.addWidget(QLabel("Records relacionados"))
        identity_layout.addWidget(self._identity_table)
        identity_layout.addWidget(QLabel("Instancias del INSTANCE_COLLECTION"))
        identity_layout.addWidget(self._instances_table)

        tabs.addTab(details_tab, "Informacion basica")
        tabs.addTab(identity_tab, "Identidad")
        tabs.addTab(stats_tab, "Estadisticas")
        tabs.addTab(files_tab, "Archivos")
        right_layout.addWidget(tabs)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([420, 760])
        root_layout.addWidget(splitter, 1)
        return root

    def _make_table_resizable(self, table: QTableWidget) -> None:
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)

    def _populate_tree(self) -> None:
        self._tree.clear()
        grouped: dict[str, list[CharacterSummary]] = defaultdict(list)
        for character in self._characters:
            grouped[character.squad].append(character)

        for squad_name in sorted(grouped):
            squad_item = QTreeWidgetItem([squad_name, "", ""])
            squad_item.setData(0, Qt.ItemDataRole.UserRole + 1, squad_name)
            squad_item.setData(0, Qt.ItemDataRole.UserRole, None)
            self._tree.addTopLevelItem(squad_item)
            for character in sorted(grouped[squad_name], key=lambda item: item.name.lower()):
                item = QTreeWidgetItem([character.name, character.status, character.internal_id])
                item.setData(0, Qt.ItemDataRole.UserRole, character)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, f"{squad_name} {character.name}")
                squad_item.addChild(item)
            squad_item.setExpanded(True)
        self._tree.resizeColumnToContents(0)

    def _populate_files(self) -> None:
        self._files_table.setRowCount(0)
        if self._analysis is None:
            return

        for data_file in self._analysis.parsed_files:
            type_counts: dict[str, int] = defaultdict(int)
            for record in data_file.records:
                type_counts[type_name(record.typecode)] += 1
            types = ", ".join(f"{name}: {count}" for name, count in sorted(type_counts.items()))
            self._append_file_row(
                data_file.path,
                str(len(data_file.records)),
                str(len(data_file.tail_data)),
                types,
            )

        for issue in self._analysis.issues:
            self._append_file_row(issue.path, "Error", "-", issue.message)

        for skipped in self._analysis.skipped_files:
            self._append_file_row(skipped, "Omitido", "-", "Archivo .hkt preservado; no parseado en Fase 1")

    def _append_file_row(self, path: Path, records: str, tail: str, notes: str) -> None:
        row = self._files_table.rowCount()
        self._files_table.insertRow(row)
        self._files_table.setItem(row, 0, QTableWidgetItem(str(path)))
        self._files_table.setItem(row, 1, QTableWidgetItem(records))
        self._files_table.setItem(row, 2, QTableWidgetItem(tail))
        self._files_table.setItem(row, 3, QTableWidgetItem(notes))

    def _show_selected_character(self) -> None:
        items = self._tree.selectedItems()
        character = items[0].data(0, Qt.ItemDataRole.UserRole) if items else None
        if not isinstance(character, CharacterSummary):
            self._details.setRowCount(0)
            self._clear_stats()
            return
        rows = [
            ("Nombre", character.name),
            ("Raza", character.race),
            ("Sexo", character.sex),
            ("Escuadron", character.squad),
            ("Estado", character.status),
            ("ID interno", character.internal_id),
            ("Indice en platoon", str(character.squad_index)),
            ("Archivo origen", str(character.source_file)),
            ("Marcado como jugador", "Si" if character.is_player_candidate else "No detectado"),
        ]
        self._details.setRowCount(len(rows))
        for row, (field, value) in enumerate(rows):
            self._details.setItem(row, 0, QTableWidgetItem(field))
            self._details.setItem(row, 1, QTableWidgetItem(value))
        self._populate_identity(character)
        self._populate_stats(character)

    def _filter_tree(self, text: str) -> None:
        query = text.strip().lower()
        for top_index in range(self._tree.topLevelItemCount()):
            squad_item = self._tree.topLevelItem(top_index)
            squad_text = (squad_item.data(0, Qt.ItemDataRole.UserRole + 1) or "").lower()
            squad_matches = not query or query in squad_text
            visible_children = 0
            for child_index in range(squad_item.childCount()):
                child = squad_item.child(child_index)
                child_text = (child.data(0, Qt.ItemDataRole.UserRole + 1) or "").lower()
                child_matches = not query or query in child_text or squad_matches
                child.setHidden(not child_matches)
                if child_matches:
                    visible_children += 1
            squad_item.setHidden(not squad_matches and visible_children == 0)
            if query and visible_children:
                squad_item.setExpanded(True)

    def _populate_identity(self, character: CharacterSummary) -> None:
        self._identity_table.setRowCount(0)
        self._instances_table.setRowCount(0)
        if self._analysis is None:
            return
        identity = build_character_identity(self._analysis, character)
        if identity is None:
            return

        for item in identity.related_records:
            row = self._identity_table.rowCount()
            self._identity_table.insertRow(row)
            numeric_preview = ", ".join(f"{key}: {value}" for key, value in all_numeric_fields(item.record)[:12])
            self._identity_table.setItem(row, 0, QTableWidgetItem(record_label(item.record)))
            self._identity_table.setItem(row, 1, QTableWidgetItem(str(item.record.record_id)))
            self._identity_table.setItem(row, 2, QTableWidgetItem(item.reason))
            self._identity_table.setItem(row, 3, QTableWidgetItem(numeric_preview))

        for instance in identity.instances:
            row = self._instances_table.rowCount()
            self._instances_table.insertRow(row)
            position = ", ".join(f"{value:g}" for value in instance.position)
            self._instances_table.setItem(row, 0, QTableWidgetItem(instance.string_id))
            self._instances_table.setItem(row, 1, QTableWidgetItem(instance.target))
            self._instances_table.setItem(row, 2, QTableWidgetItem(position))
            self._instances_table.setItem(row, 3, QTableWidgetItem(", ".join(instance.states)))

    def _populate_stats(self, character: CharacterSummary) -> None:
        if self._analysis is None:
            self._clear_stats()
            return

        self._current_character = character
        offset = self._offset_for_character(character)
        self._stats_offset_spinbox.blockSignals(True)
        self._stats_offset_spinbox.setValue(offset)
        self._stats_offset_spinbox.blockSignals(False)
        stats = find_character_stats(self._analysis, character, order_offset=offset)
        self._stats_candidates = list(find_stats_candidates(self._analysis, character, order_offset=offset))
        self._render_candidate_table()

        if stats.stats_record is None:
            self._current_stats = None
            self._stat_widgets.clear()
            self._stats_table.setRowCount(0)
            self._stats_info.setText(
                "No se encontro una fuente segura. Selecciona un bloque candidato abajo para inspeccionarlo/editarlo."
            )
            self._update_save_button_state()
            return

        self._render_stats(stats)

    def _render_stats(self, stats: CharacterStats) -> None:
        self._current_stats = stats
        self._stat_widgets.clear()
        self._stats_table.setRowCount(0)
        self._stats_info.setText(
            f"Fuente stats detectada: type {stats.stats_record.typecode}, "
            f"id {stats.stats_record.record_id} / {stats.stats_record.string_id}, "
            f"nombre '{stats.stats_record.name}'. "
            f"Encontradas: {len(stats.bindings)}; no encontradas: {len(stats.missing)}."
        )

        for binding in stats.bindings:
            row = self._stats_table.rowCount()
            self._stats_table.insertRow(row)
            self._stats_table.setItem(row, 0, QTableWidgetItem(binding.definition.display_name))

            spinbox = QDoubleSpinBox()
            spinbox.setRange(-1000.0, 1000.0)
            spinbox.setDecimals(4)
            spinbox.setSingleStep(1.0)
            key = self._stat_key(binding)
            self._stat_original_values.setdefault(key, binding.value)
            pending = self._pending_stat_changes.get(key)
            spinbox.setValue(pending.value if pending is not None else binding.value)
            spinbox.valueChanged.connect(
                lambda value, current_binding=binding, current_spinbox=spinbox: self._stat_value_changed(
                    current_binding,
                    current_spinbox,
                    value,
                )
            )
            self._style_stat_spinbox(spinbox, key)
            self._stats_table.setCellWidget(row, 1, spinbox)
            self._stat_widgets.append((binding, spinbox))

            self._stats_table.setItem(row, 2, QTableWidgetItem(binding.field_key))
            self._stats_table.setItem(row, 3, QTableWidgetItem(binding.field_kind))

        for definition in stats.missing:
            row = self._stats_table.rowCount()
            self._stats_table.insertRow(row)
            self._stats_table.setItem(row, 0, QTableWidgetItem(definition.display_name))
            self._stats_table.setItem(row, 1, QTableWidgetItem("No encontrada"))
            self._stats_table.setItem(row, 2, QTableWidgetItem("Sin campo estructurado compatible"))
            self._stats_table.setItem(row, 3, QTableWidgetItem("-"))

        self._update_save_button_state()

    def _stat_value_changed(self, binding: StatBinding, spinbox: QDoubleSpinBox, value: float) -> None:
        key = self._stat_key(binding)
        original_value = self._stat_original_values.setdefault(key, binding.value)
        set_stat_value(binding, value)

        if abs(value - original_value) > 0.00001:
            self._pending_stat_changes[key] = PendingStatChange(
                key=key,
                source_file=binding.data_file.path.resolve(),
                record_label=f"{binding.record.record_id} / {binding.record.string_id} / {binding.record.name}",
                stat_name=binding.definition.display_name,
                field_kind=binding.field_kind,
                field_key=binding.field_key,
                original_value=original_value,
                value=value,
            )
        else:
            self._pending_stat_changes.pop(key, None)

        self._modified_paths = {change.source_file for change in self._pending_stat_changes.values()}
        self._style_stat_spinbox(spinbox, key)
        self._update_save_button_state()
        self.statusBar().showMessage(f"Cambios pendientes: {len(self._pending_stat_changes)}")

    def _stat_key(self, binding: StatBinding) -> StatKey:
        return (
            binding.data_file.path.resolve(),
            binding.record.typecode,
            binding.record.record_id,
            binding.record.string_id,
            binding.field_kind,
            binding.field_key,
        )

    def _style_stat_spinbox(self, spinbox: QDoubleSpinBox, key: StatKey) -> None:
        if key in self._pending_stat_changes:
            spinbox.setStyleSheet(
                "QDoubleSpinBox { background: #3c321f; color: #ffe7a6; border: 1px solid #d19a3a; }"
            )
            return
        spinbox.setStyleSheet("")

    def _update_save_button_state(self) -> None:
        pending_count = len(self._pending_stat_changes)
        self._save_stats_button.setEnabled(pending_count > 0)
        if pending_count:
            self._save_stats_button.setText(f"Guardar estadisticas ({pending_count})")
        else:
            self._save_stats_button.setText("Guardar estadisticas")

    def _stats_offset_changed(self, value: int) -> None:
        if self._current_character is None:
            return
        self._stats_order_offsets[self._current_character.source_file.resolve()] = value
        self._populate_stats(self._current_character)

    def _offset_for_character(self, character: CharacterSummary) -> int:
        return self._stats_order_offsets.get(character.source_file.resolve(), 0)

    def _render_candidate_table(self) -> None:
        self._candidates_table.setRowCount(0)
        for index, candidate in enumerate(self._stats_candidates):
            row = self._candidates_table.rowCount()
            self._candidates_table.insertRow(row)
            source = f"type {candidate.record.typecode}"
            item = QTableWidgetItem(source)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self._candidates_table.setItem(row, 0, item)
            self._candidates_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    f"{candidate.record.record_id} / {candidate.record.string_id} / {candidate.record.name}"
                ),
            )
            self._candidates_table.setItem(row, 2, QTableWidgetItem(candidate.reason))
            self._candidates_table.setItem(row, 3, QTableWidgetItem(str(candidate.binding_count)))
            preview = ", ".join(f"{name}: {value:g}" for name, value in candidate.preview)
            self._candidates_table.setItem(row, 4, QTableWidgetItem(preview))
        self._use_candidate_button.setEnabled(bool(self._stats_candidates))

    def _use_selected_candidate(self) -> None:
        if self._current_character is None:
            return
        items = self._candidates_table.selectedItems()
        if not items:
            QMessageBox.information(self, "Selecciona un bloque", "Selecciona un bloque STATS candidato.")
            return
        row = items[0].row()
        index_item = self._candidates_table.item(row, 0)
        if index_item is None:
            return
        index = index_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or index < 0 or index >= len(self._stats_candidates):
            return
        candidate = self._stats_candidates[index]
        stats = build_character_stats_from_record(
            self._current_character,
            candidate.data_file,
            candidate.record,
        )
        self._render_stats(stats)

    def _clear_stats(self) -> None:
        self._current_stats = None
        self._current_character = None
        self._stats_candidates.clear()
        self._stat_widgets.clear()
        self._identity_table.setRowCount(0)
        self._instances_table.setRowCount(0)
        self._stats_table.setRowCount(0)
        self._candidates_table.setRowCount(0)
        self._stats_info.setText("Selecciona un personaje para ver estadisticas.")
        self._use_candidate_button.setEnabled(False)
        self._update_save_button_state()

    def _save_current_stats(self) -> None:
        if self._analysis is None:
            return

        if not self._pending_stat_changes:
            QMessageBox.information(self, "Sin cambios", "No hay estadisticas modificadas.")
            return

        changed = list(self._pending_stat_changes.values())
        lines = [
            f"{change.stat_name}: {change.original_value:g} -> {change.value:g} ({change.record_label})"
            for change in changed
        ]
        save_as_copy = self._copy_checkbox.isChecked()
        create_backup = self._backup_checkbox.isChecked()
        target_text = (
            "Se creara una copia nueva de la carpeta de save y se escribiran ahi los cambios."
            if save_as_copy
            else "Se escribiran los cambios en la partida actual."
        )
        backup_text = (
            "Tambien se creara backup antes de escribir."
            if create_backup and not save_as_copy
            else "No se creara backup porque la partida original no se tocara."
            if save_as_copy
            else "No se creara backup."
        )
        answer = QMessageBox.question(
            self,
            "Guardar estadisticas",
            f"{target_text}\n{backup_text}\n\n"
            + "\n".join(lines[:12])
            + ("\n..." if len(lines) > 12 else "")
            + "\n\nContinuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        modified_paths = {change.source_file for change in changed}

        try:
            if save_as_copy:
                copy_path = save_modified_files_to_copy(self._analysis, modified_paths)
                self._pending_stat_changes.clear()
                self._stat_original_values.clear()
                self.open_save_folder(copy_path)
                QMessageBox.information(
                    self,
                    "Copia guardada",
                    f"Copia creada con las estadisticas nuevas en:\n{copy_path}",
                )
                self.statusBar().showMessage(f"Copia guardada: {copy_path}")
                return

            backup_path = save_modified_files(
                self._analysis,
                modified_paths,
                create_backup=create_backup,
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary shows any save failure.
            QMessageBox.critical(self, "Error guardando", str(exc))
            return

        self._pending_stat_changes.clear()
        self._stat_original_values.clear()
        backup_line = f"\n\nBackup creado en:\n{backup_path}" if backup_path is not None else "\n\nBackup desactivado."
        QMessageBox.information(
            self,
            "Guardado completado",
            f"Estadisticas guardadas.{backup_line}",
        )
        self.statusBar().showMessage(
            f"Guardado completado. Backup: {backup_path}" if backup_path is not None else "Guardado completado."
        )
        self.refresh()

    def _set_summary(self, marker_found: bool) -> None:
        if self._analysis is None:
            return
        layout = self._analysis.layout
        parsed_count = len(self._analysis.parsed_files)
        issue_count = len(self._analysis.issues)
        marker_text = (
            "Se detecto marca de escuadron del jugador."
            if marker_found
            else "No se detecto una marca fiable de jugador; se muestran candidatos de platoon."
        )
        self._summary_label.setText(
            f"{layout.root} | personajes: {len(self._characters)} | "
            f"platoon: {len(layout.platoon_files)} | zone: {len(layout.zone_files)} | "
            f"archivos parseados: {parsed_count} | incidencias: {issue_count}. {marker_text}"
        )
        self.statusBar().showMessage("Analisis completado en modo solo lectura.")
