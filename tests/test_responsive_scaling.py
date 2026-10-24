"""Unit tests for the responsive type/layout scale in tkinter_theme.

The scale math, font parsing and dialog-geometry logic are pure Python;
they are exercised here without creating a Tk window, so the suite runs
on Linux even though tkinter may not be installed and the app itself is
Windows-only.

Run from the repo root:

    python -m unittest tests.test_responsive_scaling -v
"""

from __future__ import annotations

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tkinter_theme evaluates tkinter/ttk names in annotations at import time,
# and several helpers use isinstance(). A tiny stub keeps the import
# working on machines without tkinter; a real installation is preferred.
try:  # pragma: no cover - depends on the host
    import tkinter  # noqa: F401
    from tkinter import ttk  # noqa: F401
except Exception:  # pragma: no cover - Linux dev boxes without Tk
    class _TclError(Exception):
        pass

    class _Widget:
        pass

    tk = types.ModuleType("tkinter")
    tk.TclError = _TclError
    tk.Tk = _Widget
    tk.Widget = _Widget
    tk.Frame = _Widget
    tk.Label = _Widget
    tk.Toplevel = _Widget
    tk.StringVar = lambda *a, **k: None
    tk.PhotoImage = lambda *a, **k: None
    sys.modules["tkinter"] = tk

    ttk = types.ModuleType("tkinter.ttk")
    ttk.Style = type("Style", (), {})
    ttk.Frame = _Widget
    ttk.Label = _Widget
    ttk.LabelFrame = _Widget
    ttk.Widget = _Widget
    sys.modules["tkinter.ttk"] = ttk
    tk.ttk = ttk

import tkinter_theme as th  # noqa: E402


class ScaleMathTests(unittest.TestCase):
    def test_design_size_is_one(self):
        self.assertAlmostEqual(th.compute_ui_scale(780, 760), 1.0)

    def test_upper_clamp(self):
        self.assertAlmostEqual(th.compute_ui_scale(4000, 3000), 1.25)

    def test_lower_clamp(self):
        self.assertAlmostEqual(th.compute_ui_scale(400, 400), 0.90)

    def test_smaller_ratio_wins(self):
        # Wide but short: the height ratio (0.5) governs, then clamps.
        self.assertAlmostEqual(th.compute_ui_scale(4000, 380), 0.90)
        # Tall but narrow: the width ratio governs.
        self.assertAlmostEqual(th.compute_ui_scale(780, 3000), 1.0)

    def test_unmapped_and_invalid(self):
        self.assertAlmostEqual(th.compute_ui_scale(1, 1), 1.0)
        self.assertAlmostEqual(th.compute_ui_scale(0, 760), 1.0)
        self.assertAlmostEqual(th.compute_ui_scale(None, 760), 1.0)

    def test_font_scaling_rounds_and_floors(self):
        self.assertEqual(th._scale_font_spec(("Segoe UI", 10, "bold"), 1.25),
                         ("Segoe UI", 13, "bold"))
        self.assertEqual(th._scale_font_spec(("Segoe UI", 10), 0.90),
                         ("Segoe UI", 9))
        # Never below the 7pt floor.
        self.assertEqual(th._scale_font_spec(("Segoe UI", 7), 0.5),
                         ("Segoe UI", 7))

    def test_padding_scaling(self):
        self.assertEqual(th._scale_padding(6, 1.25), 8)
        self.assertEqual(th._scale_padding(6, 0.90), 5)
        self.assertEqual(th._scale_padding((14, 7), 1.25), (18, 9))
        self.assertEqual(th._scale_padding((0, 0), 0.90), (1, 1))

    def test_font_key_normalises_normal(self):
        self.assertEqual(th._font_key(("Segoe UI", 10, "normal")),
                         th._font_key(("Segoe UI", 10)))
        self.assertNotEqual(th._font_key(("Segoe UI", 10, "bold")),
                            th._font_key(("Segoe UI", 10)))

    def test_parse_font_spec(self):
        class FakeTk:
            @staticmethod
            def splitlist(value):
                value = str(value)
                if value.startswith("{"):
                    family, rest = value[1:].split("}", 1)
                    return (family,) + tuple(rest.split())
                return tuple(value.split())

        class Fake:
            tk = FakeTk()

        f = Fake()
        self.assertEqual(th._parse_font_spec(f, "{Segoe UI} 10 normal"),
                         ("Segoe UI", 10, "normal"))
        self.assertEqual(th._parse_font_spec(f, ("Segoe UI", 10)),
                         ("Segoe UI", 10))
        # A named font is shared and must not be rescaled per widget.
        self.assertIsNone(th._parse_font_spec(f, "TkDefaultFont"))
        # Negative sizes are pixel sizes, intentionally left alone.
        self.assertIsNone(th._parse_font_spec(f, "Segoe UI -12"))
        self.assertIsNone(th._parse_font_spec(f, ""))


class FakeTk:
    def __init__(self, owner):
        self.owner = owner

    def splitlist(self, value):
        return str(value).split()

    def call(self, *args):
        if args[:2] == ("wm", "resizable"):
            return "%d %d" % self.owner.resizable_flags
        raise TypeError("unexpected Tcl call: %r" % (args,))


class FakeWindow:
    def __init__(self, size=(800, 600), mapped=True, resizable=(0, 0),
                 screen=(1920, 1080)):
        self.size = tuple(size)
        self.mapped = mapped
        self.resizable_flags = tuple(resizable)
        self.screen = tuple(screen)
        self.tk = FakeTk(self)
        self.geometry_calls = 0

    def __str__(self):
        return ".dialog"

    def winfo_ismapped(self):
        return self.mapped

    def winfo_width(self):
        return self.size[0]

    def winfo_height(self):
        return self.size[1]

    def winfo_screenwidth(self):
        return self.screen[0]

    def winfo_screenheight(self):
        return self.screen[1]

    def geometry(self, spec):
        self.geometry_calls += 1
        w, h = spec.split("x")
        self.size = (int(w), int(h))


class DialogGeometryTests(unittest.TestCase):
    def test_fixed_dialog_scales_and_returns(self):
        win = FakeWindow()
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (1000, 750))
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (1000, 750))       # no compounding
        th._rescale_toplevel_geometry(win, 0.90)
        self.assertEqual(win.size, (720, 540))
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (1000, 750))

    def test_resizable_window_is_untouched(self):
        win = FakeWindow(resizable=(1, 1))
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (800, 600))
        self.assertEqual(win.geometry_calls, 0)

    def test_unmapped_window_is_left_for_map(self):
        win = FakeWindow(mapped=False)
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (800, 600))
        self.assertEqual(win.geometry_calls, 0)

    def test_screen_cap(self):
        win = FakeWindow(screen=(900, 700))
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (840, 600))

    def test_app_resize_is_not_compounded(self):
        win = FakeWindow()
        th._rescale_toplevel_geometry(win, 1.25)     # 1000x750 at 125%
        win.size = (750, 500)                        # app shrank it
        th._rescale_toplevel_geometry(win, 1.0)      # back to 100%
        self.assertEqual(win.size, (600, 400))
        th._rescale_toplevel_geometry(win, 1.25)
        self.assertEqual(win.size, (750, 500))


if __name__ == "__main__":
    unittest.main()
