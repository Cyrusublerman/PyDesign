from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    from pydesign.gui.app import MainWindow, PageCanvas
except ImportError:
    QApplication = None  # type: ignore[assignment,misc]
    MainWindow = None  # type: ignore[assignment,misc]
    PageCanvas = None  # type: ignore[assignment,misc]


@unittest.skipUnless(
    QApplication is not None, "PySide6 or a required system library is unavailable"
)
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert QApplication is not None
        cls.application = QApplication.instance() or QApplication([])

    def test_shell_and_canvas_construct(self) -> None:
        assert MainWindow is not None
        window = MainWindow()
        self.assertEqual(window.state_label.text(), "No project")
        window.close()

    def test_display_list_creates_page_items(self) -> None:
        assert PageCanvas is not None
        canvas = PageCanvas()
        canvas.set_layout(
            {
                "pages": [
                    {
                        "id": "page",
                        "width": 100,
                        "height": 200,
                        "operations": [
                            {
                                "op": "rectangle",
                                "object_id": "box",
                                "x": 10,
                                "y": 10,
                                "width": 20,
                                "height": 30,
                                "fill": "#ff6600",
                                "stroke": None,
                                "stroke_width": 1,
                            }
                        ],
                    }
                ]
            }
        )
        self.assertGreaterEqual(len(canvas.canvas_scene.items()), 3)


if __name__ == "__main__":
    unittest.main()
