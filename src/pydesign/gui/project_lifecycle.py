"""GUI orchestration for portable project-folder lifecycle actions."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QToolBar,
)

from pydesign.gui.settings import ApplicationSettings
from pydesign.runtime import (
    UnsafeProjectLocationError,
    create_project,
    duplicate_project,
    is_bundled_example,
    load_project_config,
    package_project,
)
from pydesign.runtime.project import compute_project_revision


class ProjectLifecycleMixin:
    """Reusable project actions for ``MainWindow`` without expanding its responsibilities."""

    settings: ApplicationSettings
    project_root: Path | None
    last_good_revision: str | None

    def install_project_actions(
        self, file_menu: QMenu, toolbar: QToolBar, save_action: QAction
    ) -> None:
        new_action = QAction("New Project…", self)  # type: ignore[arg-type]
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        open_action = QAction("Open Project…", self)  # type: ignore[arg-type]
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.choose_project)
        save_as_action = QAction("Save Project As…", self)  # type: ignore[arg-type]
        save_as_action.triggered.connect(self.save_project_as)
        duplicate_action = QAction("Duplicate Project…", self)  # type: ignore[arg-type]
        duplicate_action.triggered.connect(self.duplicate_current_project)
        package_action = QAction("Package Project…", self)  # type: ignore[arg-type]
        package_action.triggered.connect(self.package_current_project)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        self.recent_projects_menu = file_menu.addMenu("Open Recent")
        self.recent_projects_menu.aboutToShow.connect(self.rebuild_recent_projects_menu)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addAction(duplicate_action)
        file_menu.addAction(package_action)
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)

    def new_project(self) -> None:
        if not self.confirm_project_switch():
            return
        destination = self._choose_project_destination("Create PyDesign Project", "Untitled")
        if destination is None:
            return
        name = destination.name
        config = self._with_checkout_confirmation(
            lambda allow: create_project(
                destination, name=name, allow_in_source_checkout=allow
            )
        )
        if config is not None:
            self.open_project(config.root, offer_example_copy=False)  # type: ignore[attr-defined]

    def choose_project(self) -> None:
        recent = self.settings.recent_projects()
        initial = recent[0].parent if recent else self.settings.default_projects_directory()
        directory = QFileDialog.getExistingDirectory(
            self, "Open PyDesign project", str(_existing_parent(initial))  # type: ignore[arg-type]
        )
        if directory:
            self.open_project(Path(directory))  # type: ignore[attr-defined]

    def prepare_project_open(self, root: Path, *, offer_example_copy: bool) -> Path | None:
        resolved = root.expanduser().resolve()
        if not offer_example_copy or not is_bundled_example(resolved):
            return resolved
        choice = QMessageBox.question(
            self,  # type: ignore[arg-type]
            "Bundled example",
            "This project is maintained as part of the PyDesign source repository. "
            "Create an editable copy outside the repository?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return None
        if choice == QMessageBox.StandardButton.No:
            return resolved
        destination = self._choose_project_destination(
            "Copy Bundled Example", f"{resolved.name} Copy"
        )
        if destination is None:
            return None
        config = self._with_checkout_confirmation(
            lambda allow: duplicate_project(
                resolved,
                destination,
                name=destination.name,
                allow_in_source_checkout=allow,
            )
        )
        return config.root if config is not None else None

    def record_recent_project(self, root: Path) -> None:
        self.settings.add_recent_project(root)

    def confirm_project_switch(self) -> bool:
        if not self.editor.document().isModified():  # type: ignore[attr-defined]
            return True
        choice = QMessageBox.question(
            self,  # type: ignore[arg-type]
            "Unsaved source",
            "Save the current Python source before opening another project?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            return bool(self.save_source())  # type: ignore[attr-defined]
        recovery = getattr(self, "recovery", None)
        active_source = getattr(self, "active_source_path", None)
        if recovery is not None and active_source is not None:
            recovery.clear(active_source)
        self.editor.document().setModified(False)  # type: ignore[attr-defined]
        return True

    def rebuild_recent_projects_menu(self) -> None:
        self.recent_projects_menu.clear()
        projects = self.settings.recent_projects()
        if not projects:
            empty = self.recent_projects_menu.addAction("No recent projects")
            empty.setEnabled(False)
            return
        for project in projects:
            action = self.recent_projects_menu.addAction(project.name)
            action.setToolTip(str(project))
            action.triggered.connect(
                lambda _checked=False, selected=project: getattr(self, "open_project")(
                    selected
                )
            )

    def save_project_as(self) -> None:
        if not self._save_before_project_operation():
            return
        assert self.project_root is not None
        destination = self._choose_project_destination(
            "Save PyDesign Project As", f"{self.project_root.name} Copy"
        )
        if destination is None:
            return
        config = self._duplicate_to(destination)
        if config is not None:
            self.open_project(config.root, offer_example_copy=False)  # type: ignore[attr-defined]

    def duplicate_current_project(self) -> None:
        if not self._save_before_project_operation():
            return
        assert self.project_root is not None
        destination = self._choose_project_destination(
            "Duplicate PyDesign Project", f"{self.project_root.name} Copy"
        )
        if destination is None:
            return
        config = self._duplicate_to(destination)
        if config is not None:
            QMessageBox.information(
                self,  # type: ignore[arg-type]
                "Project duplicated",
                f"Created an independent project at:\n{config.root}",
            )

    def package_current_project(self) -> None:
        if not self._save_before_project_operation():
            return
        assert self.project_root is not None
        try:
            revision = compute_project_revision(load_project_config(self.project_root))
        except (OSError, ValueError) as error:
            self._show_project_error(str(error))
            return
        if revision != self.last_good_revision:
            self._show_project_error(
                "Run the current saved project successfully before packaging it. "
                "Packages cannot be created from a stale or failed preview."
            )
            return
        suggested = self.project_root.parent / f"{self.project_root.name}-package.zip"
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,  # type: ignore[arg-type]
            "Package PyDesign Project",
            str(suggested),
            "ZIP archives (*.zip);;All files (*)",
        )
        if not filename:
            return
        output = Path(filename)
        if output.suffix.lower() != ".zip":
            output = output.with_suffix(".zip")
        try:
            result = package_project(self.project_root, output)
        except (OSError, ValueError) as error:
            self._show_project_error(str(error))
            return
        QMessageBox.information(
            self,  # type: ignore[arg-type]
            "Project packaged",
            f"Packaged {result.file_count} authored files to:\n{result.output}",
        )

    def save_application_state(self) -> None:
        self.settings.save_window(
            geometry=bytes(self.saveGeometry()),  # type: ignore[attr-defined]
            state=bytes(self.saveState()),  # type: ignore[attr-defined]
        )

    def _duplicate_to(self, destination: Path) -> Any | None:
        assert self.project_root is not None
        return self._with_checkout_confirmation(
            lambda allow: duplicate_project(
                self.project_root,
                destination,
                name=destination.name,
                allow_in_source_checkout=allow,
            )
        )

    def _save_before_project_operation(self) -> bool:
        if self.project_root is None:
            self._show_project_error("Open a project first.")
            return False
        return bool(self.save_source())  # type: ignore[attr-defined]

    def _with_checkout_confirmation(
        self, operation: Callable[[bool], Any]
    ) -> Any | None:
        try:
            return operation(False)
        except UnsafeProjectLocationError as error:
            choice = QMessageBox.warning(
                self,  # type: ignore[arg-type]
                "Unsafe project location",
                f"{error}\n\nCreate there anyway? Files may be included in a Git commit.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return None
            try:
                return operation(True)
            except (OSError, ValueError) as repeated_error:
                self._show_project_error(str(repeated_error))
                return None
        except (OSError, ValueError) as error:
            self._show_project_error(str(error))
            return None

    def _choose_project_destination(self, title: str, suggested_name: str) -> Path | None:
        default_root = self.settings.default_projects_directory()
        try:
            default_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            default_root = _existing_parent(default_root)
        parent = QFileDialog.getExistingDirectory(
            self, title, str(default_root)  # type: ignore[arg-type]
        )
        if not parent:
            return None
        name, accepted = QInputDialog.getText(
            self,  # type: ignore[arg-type]
            "Project name",
            "Folder and project name:",
            text=suggested_name,
        )
        cleaned = " ".join(name.split()).strip()
        if not accepted or not cleaned:
            return None
        destination = Path(parent) / cleaned
        self.settings.set_default_projects_directory(destination.parent)
        return destination

    def _show_project_error(self, message: str) -> None:
        QMessageBox.critical(self, "Project operation failed", message)  # type: ignore[arg-type]


def _existing_parent(path: Path) -> Path:
    candidate = path.expanduser()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate
