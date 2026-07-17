from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    from pydesign.gui.app import MainWindow, PageCanvas
    from pydesign.gui.canvas import EditableBezierItem
except ImportError:
    QApplication = None  # type: ignore[assignment,misc]
    MainWindow = None  # type: ignore[assignment,misc]
    PageCanvas = None  # type: ignore[assignment,misc]
    EditableBezierItem = None  # type: ignore[assignment,misc]


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
                            },
                            {
                                "op": "bezier_path",
                                "object_id": "curve",
                                "commands": [
                                    {"command": "move", "x": 10, "y": 60},
                                    {
                                        "command": "curve",
                                        "control_1_x": 30,
                                        "control_1_y": 20,
                                        "control_2_x": 60,
                                        "control_2_y": 100,
                                        "x": 90,
                                        "y": 60,
                                    },
                                ],
                                "fill": None,
                                "stroke": "#5b32a3",
                                "stroke_width": 1,
                            },
                        ],
                    }
                ]
            }
        )
        self.assertGreaterEqual(len(canvas.canvas_scene.items()), 3)
        box = canvas._object_items["box"]
        box.setSelected(True)
        self.assertTrue(box.resize_handle.isVisible())
        box.set_frame_size(40, 50)
        self.assertEqual(box.frame_points()[2:], (40.0, 50.0))
        self.assertIn("curve", canvas._object_items)
        curve = canvas._object_items["curve"]
        assert EditableBezierItem is not None
        self.assertIsInstance(curve, EditableBezierItem)
        assert isinstance(curve, EditableBezierItem)
        curve.setSelected(True)
        self.assertTrue(all(handle.isVisible() for handle in curve.handles))


if __name__ == "__main__":
    unittest.main()
