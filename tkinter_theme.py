"""
exFAT Image Builder — tkinter/ttk theme module
==============================================

Drop-in dark theme that mirrors the design system in colors_and_type.css.
The app already uses tkinter + ttk; this module gives every widget the
"professional tools" look without rewriting the rest of the codebase.

USAGE
-----
At the top of `exfat_builder.py`, after creating your root:

    import tkinter as tk
    from tkinter import ttk
    from tkinter_theme import apply_theme, COLORS, FONTS

    root = tk.Tk()
    apply_theme(root)                 # <-- single call themes everything
    install_responsive_scaling(root)  # type follows the window size
    root.configure(bg=COLORS["bg_1"])
    root.title("exFAT Image Builder")

After this:
    ttk.Button(root, text="Build All", style="Primary.TButton").pack()
    ttk.Button(root, text="Cancel",    style="Ghost.TButton").pack()
    ttk.Button(root, text="⚠ Backport", style="Warn.TButton").pack()
    ttk.Button(root, text="Delete",    style="Danger.TButton").pack()

STYLE NAMES (use as `style="..."` on a ttk widget)
--------------------------------------------------
Buttons        : Primary.TButton, Secondary.TButton, Ghost.TButton,
                 Warn.TButton, Danger.TButton, Success.TButton
Frames         : Card.TFrame, Panel.TFrame, Surface.TFrame
Labels         : H1.TLabel, H2.TLabel, H3.TLabel, Eyebrow.TLabel,
                 Body.TLabel, Muted.TLabel, Meta.TLabel, Mono.TLabel,
                 Accent.TLabel, Success.TLabel, Warn.TLabel, Danger.TLabel
Entry/Combo    : Field.TEntry, Field.TCombobox  (light-on-dark — matches app)
Notebook tabs  : (default — already themed)
Progress       : Build.Horizontal.TProgressbar
Treeview       : Library.Treeview  (for game grid / queue list)
Scrollbar      : (default — already themed)
LabelFrame     : Card.TLabelframe  (for sectioned cards in Settings/Advanced)
Separator      : Hairline.TSeparator

NON-TTK WIDGETS (tk.Listbox, tk.Text, tk.Canvas) get their defaults set via
root.option_add — colors are picked up automatically.
"""

import tkinter as tk
from tkinter import ttk
import platform

# ────────────────────────────────────────────────────────────────────
# COLOR TOKENS  (1:1 with colors_and_type.css)
# ────────────────────────────────────────────────────────────────────
COLORS = {
    # ── Sony PS5-inspired neutral dark palette ───────────────────────
    # Canonical values (the only hues used anywhere in the app):
    #   #101216 bg · #171A21 secondary · #20242C elevated
    #   #292F39 hover · #303640 borders
    #   #0070D1 primary · #1685E5 secondary · #2EA3FF active
    #   #F5F7FA text · #A7AFBA secondary text · #737D8A muted
    #   #42C786 success · #F0B64A warning · #F16C75 error
    #
    # The extra tokens below (bg_5, border_4, fg_2/fg_5/fg_6 and the
    # *_hi hover shades) are neutral/tonal steps between those canonical
    # values. There is no purple, violet or magenta anywhere in this
    # table — including the legacy `purple`/`teal` aliases, which now
    # resolve inside the PlayStation blue family.

    # Surfaces
    "bg_0":     "#101216",   # deepest surface (app / terminal / logs)
    "bg_1":     "#101216",   # page background
    "bg_2":     "#171A21",   # secondary surface / cards
    "bg_3":     "#20242C",   # elevated surface / panels
    "bg_4":     "#292F39",   # controls, inputs, hover
    "bg_5":     "#303640",   # strong hover / pressed control

    # Borders
    "border_1": "#171A21",
    "border_2": "#20242C",
    "border_3": "#303640",
    "border_4": "#3A414D",   # strong / focused outline

    # Foregrounds
    "fg_0":     "#F5F7FA",   # primary text
    "fg_1":     "#F5F7FA",
    "fg_2":     "#D6DCE4",
    "fg_3":     "#A7AFBA",   # secondary text
    "fg_4":     "#737D8A",   # muted text
    "fg_5":     "#5C6672",
    "fg_6":     "#464E59",   # disabled

    # Inputs — dark fields, never white
    "field_bg": "#20242C",
    "field_fg": "#F5F7FA",
    "field_select_bg": "#0070D1",
    "field_select_fg": "#F5F7FA",

    # Accent — PlayStation blue
    "accent":         "#0070D1",
    "accent_hi":      "#2EA3FF",
    "accent_lo":      "#0B2A47",
    "accent_08":      "#13202E",   # opaque blue tint over bg_1
    "accent_15":      "#14385C",   # selected row / stronger blue tint
    "accent_pressed": "#0059A8",

    # Status
    "success":    "#42C786",
    "success_hi": "#6FDFA6",   # hover / text-on-dark step
    "success_bg": "#12261C",
    "success_ok": "#42C786",   # terminal log text (no neon green)

    "warn":       "#F0B64A",
    "warn_hi":    "#FFD27A",
    "warn_bg":    "#2B2412",

    "danger":     "#F16C75",
    "danger_hi":  "#FF939B",
    "danger_bg":  "#2B1519",

    "info_bg":    "#13202E",

    # Confidence dots (Dump Rename)
    "conf_clean": "#42C786",
    "conf_guess": "#F0B64A",
    "conf_fail":  "#F16C75",

    # Legacy semantic aliases — kept so existing call sites keep working.
    # They intentionally resolve to blue (never purple): `purple` is the
    # secondary action blue, `teal` the active blue used for ffpkg flows.
    "purple":     "#1685E5",
    "purple_hi":  "#2EA3FF",
    "teal":       "#2EA3FF",
    "teal_hi":    "#63B8FF",
    "teal_bg":    "#13202E",
    "teal_lo":    "#1D3D5C",
}

# ────────────────────────────────────────────────────────────────────
# FONTS
# ────────────────────────────────────────────────────────────────────
# tkinter takes (family, size, weight) tuples. Sizes here mirror the CSS
# scale (px → tk pt; close enough on Windows where 1pt ≈ 1.33px).
#
# Typography is deliberately single-family: Segoe UI for all UI text and
# Consolas for monospace/terminal surfaces. Both ship with Windows, so the
# app looks identical on every machine — no optional third-party fonts,
# no font-stack probing at startup. Non-Windows fallbacks exist only so
# the module remains importable for tests/tools.
_SANS = "Segoe UI" if platform.system() == "Windows" else (
    ".AppleSystemUIFont" if platform.system() == "Darwin" else "Sans")
_MONO = "Consolas" if platform.system() == "Windows" else (
    "Menlo" if platform.system() == "Darwin" else "DejaVu Sans Mono")

FONTS = {
    "h1":      (_SANS, 22, "bold"),
    "h2":      (_SANS, 15, "bold"),
    "h3":      (_SANS, 12, "bold"),
    "eyebrow": (_SANS,  9, "bold"),    # render uppercase manually
    "body":    (_SANS, 10, "normal"),
    "body_b":  (_SANS, 10, "bold"),
    "label":   (_SANS,  9, "normal"),
    "meta":    (_SANS,  8, "normal"),
    "button":  (_SANS, 10, "normal"),
    "tab":     (_SANS, 10, "normal"),
    "mono":    (_MONO, 10, "normal"),
    "mono_sm": (_MONO,  9, "normal"),
}


# ────────────────────────────────────────────────────────────────────
# THEME APPLICATION
# ────────────────────────────────────────────────────────────────────
def apply_theme(root: tk.Tk) -> ttk.Style:
    """Apply the dark theme to `root`. Returns the ttk.Style for further tweaks."""
    # Typography is fixed at module load (Segoe UI / Consolas on Windows).
    # No font probing: the theme must render identically on every machine.
    C = COLORS
    F = FONTS

    style = ttk.Style(root)
    # 'clam' is the only built-in theme that fully respects color overrides
    # on Windows. Without this, ttk falls back to the native Windows theme
    # and most of these configure() calls will be ignored.
    style.theme_use("clam")

    # ── tk option defaults (cover non-ttk widgets: Listbox, Text, Menu, Canvas) ──
    root.configure(bg=C["bg_1"])
    root.option_add("*background",        C["bg_1"])
    root.option_add("*foreground",        C["fg_1"])
    root.option_add("*Font",              F["body"])
    root.option_add("*selectBackground",  C["accent"])
    root.option_add("*selectForeground",  C["fg_0"])
    root.option_add("*insertBackground",  C["fg_0"])
    root.option_add("*highlightThickness", 0)
    root.option_add("*borderWidth",        0)

    root.option_add("*Listbox.background",         C["bg_2"])
    root.option_add("*Listbox.foreground",         C["fg_1"])
    root.option_add("*Listbox.selectBackground",   C["accent"])
    root.option_add("*Listbox.selectForeground",   C["fg_0"])
    root.option_add("*Listbox.borderWidth",        0)
    root.option_add("*Listbox.highlightThickness", 1)
    root.option_add("*Listbox.highlightBackground", C["border_2"])
    root.option_add("*Listbox.highlightColor",     C["accent"])
    root.option_add("*Listbox.activeStyle",        "none")

    root.option_add("*Text.background",      C["bg_0"])
    root.option_add("*Text.foreground",      C["fg_1"])
    root.option_add("*Text.insertBackground", C["accent"])
    root.option_add("*Text.borderWidth",     0)
    root.option_add("*Text.highlightThickness", 0)
    root.option_add("*Text.font",            F["mono"])
    root.option_add("*Text.padX",            8)
    root.option_add("*Text.padY",            8)

    root.option_add("*Menu.background",          C["bg_3"])
    root.option_add("*Menu.foreground",          C["fg_1"])
    root.option_add("*Menu.activeBackground",    C["accent_08"])
    root.option_add("*Menu.activeForeground",    C["accent"])
    root.option_add("*Menu.borderWidth",         1)
    root.option_add("*Menu.activeBorderWidth",   0)
    root.option_add("*Menu.relief",              "flat")

    root.option_add("*Canvas.background",       C["bg_1"])
    root.option_add("*Canvas.highlightThickness", 0)

    # Dialogs / popovers: Toplevels and their plain tk children inherit the
    # same surfaces as the main window so modal forms never flash a light
    # background before their own colours are applied.
    root.option_add("*Toplevel.background",      C["bg_1"])
    root.option_add("*Toplevel*Label.font",      F["body"])

    # ── ttk base ──
    style.configure(".",
                    background=C["bg_1"],
                    foreground=C["fg_1"],
                    fieldbackground=C["field_bg"],
                    bordercolor=C["border_2"],
                    lightcolor=C["border_2"],
                    darkcolor=C["border_2"],
                    troughcolor=C["bg_4"],
                    focuscolor=C["accent"],
                    selectbackground=C["accent"],
                    selectforeground=C["fg_0"],
                    insertcolor=C["fg_0"],
                    font=F["body"])

    # ── TFrame ──
    style.configure("TFrame",         background=C["bg_1"])
    style.configure("Surface.TFrame", background=C["bg_1"])
    style.configure("Card.TFrame",    background=C["bg_2"], relief="flat", borderwidth=1)
    style.configure("Panel.TFrame",   background=C["bg_3"], relief="flat", borderwidth=1)

    # ── TLabelframe (sectioned cards) ──
    style.configure("TLabelframe",
                    background=C["bg_2"],
                    bordercolor=C["border_2"],
                    relief="solid",
                    borderwidth=1)
    style.configure("TLabelframe.Label",
                    background=C["bg_2"],
                    foreground=C["fg_3"],
                    font=F["h3"])
    style.configure("Card.TLabelframe",
                    background=C["bg_2"],
                    bordercolor=C["border_3"],
                    borderwidth=1, relief="solid", padding=16)
    style.configure("Card.TLabelframe.Label",
                    background=C["bg_2"], foreground=C["fg_3"], font=F["h3"])

    # ── TLabel variants ──
    # Blue is reserved for actions and live state; headings are primary
    # text, secondary copy is fg_3/fg_4. This keeps the interface reading
    # like a console UI instead of a highlighter.
    style.configure("TLabel",        background=C["bg_1"], foreground=C["fg_1"], font=F["body"])
    style.configure("H1.TLabel",     foreground=C["fg_0"],   font=F["h1"])
    style.configure("H2.TLabel",     foreground=C["fg_0"],   font=F["h2"])
    style.configure("H3.TLabel",     foreground=C["fg_0"],   font=F["h3"])
    style.configure("Eyebrow.TLabel", foreground=C["fg_4"],  font=F["eyebrow"])
    style.configure("Body.TLabel",   foreground=C["fg_1"],   font=F["body"])
    style.configure("Muted.TLabel",  foreground=C["fg_4"],   font=F["body"])
    style.configure("Meta.TLabel",   foreground=C["fg_5"],   font=F["meta"])
    style.configure("Mono.TLabel",   foreground=C["accent_hi"], font=F["mono"], background=C["bg_3"])
    style.configure("Accent.TLabel", foreground=C["accent_hi"], font=F["body_b"])
    style.configure("Success.TLabel", foreground=C["success_hi"], font=F["body"])
    style.configure("Warn.TLabel",   foreground=C["warn_hi"], font=F["body"])
    style.configure("Danger.TLabel", foreground=C["danger_hi"], font=F["body"])
    style.configure("OnCard.TLabel", background=C["bg_2"], foreground=C["fg_1"])
    style.configure("OnCard.H3.TLabel", background=C["bg_2"], foreground=C["fg_0"], font=F["h3"])
    style.configure("OnCard.Muted.TLabel", background=C["bg_2"], foreground=C["fg_4"])

    # ── TButton — primary ──
    style.configure("TButton",
                    background=C["bg_4"],
                    foreground=C["fg_1"],
                    bordercolor=C["border_3"],
                    lightcolor=C["border_3"],
                    darkcolor=C["border_3"],
                    relief="flat",
                    padding=(14, 7),
                    font=F["button"])
    style.map("TButton",
              background=[("active", C["bg_5"]),
                          ("pressed", C["bg_3"]),
                          ("disabled", C["bg_2"])],
              foreground=[("disabled", C["fg_6"])],
              bordercolor=[("focus", C["accent"]),
                           ("active", C["border_4"])])

    style.configure("Primary.TButton",
                    background=C["accent"], foreground=C["fg_0"],
                    bordercolor=C["accent"], lightcolor=C["accent"], darkcolor=C["accent"],
                    padding=(16, 8), font=F["button"], relief="flat")
    style.map("Primary.TButton",
              background=[("active", C["accent_hi"]),
                          ("pressed", C["accent_pressed"]),
                          ("disabled", C["bg_3"])],
              foreground=[("disabled", C["fg_6"])])

    style.configure("Secondary.TButton",
                    background=C["bg_4"], foreground=C["accent"],
                    bordercolor=C["accent"], lightcolor=C["accent"], darkcolor=C["accent"],
                    padding=(14, 7), relief="flat")
    style.map("Secondary.TButton",
              background=[("active", C["accent_08"]), ("pressed", C["accent_15"])])

    style.configure("Ghost.TButton",
                    background=C["bg_1"], foreground=C["fg_3"],
                    bordercolor=C["bg_1"], lightcolor=C["bg_1"], darkcolor=C["bg_1"],
                    padding=(10, 6), relief="flat")
    style.map("Ghost.TButton",
              background=[("active", C["bg_3"]), ("pressed", C["bg_4"])],
              foreground=[("active", C["fg_1"])])

    # Filled bright buttons use the darkest surface colour for their label:
    # it is the highest-contrast option on amber/green/red and keeps the
    # palette closed (no invented near-black text tones).
    style.configure("Warn.TButton",
                    background=C["warn"], foreground=C["bg_0"],
                    bordercolor=C["warn"], lightcolor=C["warn"], darkcolor=C["warn"],
                    padding=(14, 7), font=F["body_b"], relief="flat")
    style.map("Warn.TButton",
              background=[("active", C["warn_hi"]), ("pressed", C["warn"])],
              foreground=[("disabled", C["fg_6"])])

    style.configure("Danger.TButton",
                    background=C["danger"], foreground=C["bg_0"],
                    bordercolor=C["danger"], lightcolor=C["danger"], darkcolor=C["danger"],
                    padding=(14, 7), font=F["body_b"], relief="flat")
    style.map("Danger.TButton",
              background=[("active", C["danger_hi"]), ("pressed", C["danger"])],
              foreground=[("disabled", C["fg_6"])])

    style.configure("Success.TButton",
                    background=C["success"], foreground=C["bg_0"],
                    bordercolor=C["success"], lightcolor=C["success"], darkcolor=C["success"],
                    padding=(14, 7), font=F["body_b"], relief="flat")
    style.map("Success.TButton",
              background=[("active", C["success_hi"]), ("pressed", C["success"])],
              foreground=[("disabled", C["fg_6"])])

    # Backports use the secondary PlayStation blue — never purple.
    style.configure("Backport.TButton",
                    background=C["purple"], foreground=C["fg_0"],
                    bordercolor=C["purple"], lightcolor=C["purple"], darkcolor=C["purple"],
                    padding=(14, 7), font=F["body_b"], relief="flat")
    style.map("Backport.TButton",
              background=[("active", C["purple_hi"]), ("pressed", C["accent_pressed"])],
              foreground=[("disabled", C["fg_6"])])

    # ── TCheckbutton / TRadiobutton ──
    style.configure("TCheckbutton",
                    background=C["bg_1"], foreground=C["fg_1"],
                    indicatorcolor=C["bg_4"], indicatorbackground=C["bg_4"],
                    focuscolor=C["accent"], font=F["body"])
    style.map("TCheckbutton",
              indicatorcolor=[("selected", C["accent"]), ("pressed", C["accent_lo"])],
              foreground=[("disabled", C["fg_6"])])
    style.configure("OnCard.TCheckbutton", background=C["bg_2"])

    style.configure("TRadiobutton",
                    background=C["bg_1"], foreground=C["fg_1"],
                    indicatorcolor=C["bg_4"], focuscolor=C["accent"])
    style.map("TRadiobutton", indicatorcolor=[("selected", C["accent"])])
    # On-card radio: same as TRadiobutton but with bg_2 background so it
    # blends into Card.TFrame surfaces.
    style.configure("OnCard.TRadiobutton",
                    background=C["bg_2"], foreground=C["fg_1"],
                    indicatorcolor=C["bg_4"], focuscolor=C["accent"])
    style.map("OnCard.TRadiobutton",
              indicatorcolor=[("selected", C["accent"])])

    # ── TEntry ──
    # Note: the app's entries are intentionally light-on-dark — matches Windows-form
    # style. If you want fully-dark entries instead, swap field_bg → bg_4, field_fg → fg_1.
    style.configure("TEntry",
                    fieldbackground=C["field_bg"], foreground=C["field_fg"],
                    bordercolor=C["border_3"], lightcolor=C["border_3"], darkcolor=C["border_3"],
                    insertcolor=C["accent"], padding=6, relief="flat")
    style.map("TEntry",
              bordercolor=[("focus", C["accent"])],
              lightcolor=[("focus", C["accent"])],
              darkcolor=[("focus", C["accent"])])

    style.configure("Dark.TEntry",
                    fieldbackground=C["bg_4"], foreground=C["fg_1"],
                    insertcolor=C["accent"], padding=6, relief="flat",
                    bordercolor=C["border_3"], lightcolor=C["border_3"], darkcolor=C["border_3"])
    style.map("Dark.TEntry", bordercolor=[("focus", C["accent"])])

    # ── TCombobox ──
    style.configure("TCombobox",
                    fieldbackground=C["field_bg"], foreground=C["field_fg"],
                    background=C["bg_4"], arrowcolor=C["fg_2"],
                    bordercolor=C["border_3"], padding=6, relief="flat")
    style.map("TCombobox",
              fieldbackground=[("readonly", C["bg_4"])],
              foreground=[("readonly", C["fg_1"])],
              arrowcolor=[("active", C["accent"])],
              bordercolor=[("focus", C["accent"])])
    # Dropdown listbox must be themed via option_add
    root.option_add("*TCombobox*Listbox.background",       C["bg_3"])
    root.option_add("*TCombobox*Listbox.foreground",       C["fg_1"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["fg_0"])
    root.option_add("*TCombobox*Listbox.borderWidth",      0)
    root.option_add("*TCombobox*Listbox.font",             F["body"])

    # ── TNotebook (the main tab strip) ──
    style.configure("TNotebook",
                    background=C["bg_1"], bordercolor=C["bg_1"],
                    borderwidth=0, tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab",
                    background=C["bg_1"], foreground=C["fg_4"],
                    bordercolor=C["bg_1"], lightcolor=C["bg_1"], darkcolor=C["bg_1"],
                    padding=(16, 9), font=F["tab"])
    style.map("TNotebook.Tab",
              background=[("selected", C["bg_2"]), ("active", C["bg_3"])],
              foreground=[("selected", C["accent_hi"]), ("active", C["fg_1"])],
              bordercolor=[("selected", C["accent"])],
              lightcolor=[("selected", C["accent"])])
    # Custom layout: thicker bottom border on selected tab (the blue underline)
    style.layout("TNotebook.Tab", [
        ("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})
            ]})
        ]})
    ])

    # ── Horizontal.TProgressbar ──
    style.configure("Horizontal.TProgressbar",
                    troughcolor=C["bg_4"], background=C["accent"],
                    bordercolor=C["bg_4"], lightcolor=C["accent"], darkcolor=C["accent"],
                    thickness=8)
    style.configure("Build.Horizontal.TProgressbar",
                    troughcolor=C["bg_4"], background=C["accent"],
                    bordercolor=C["bg_4"], lightcolor=C["accent"], darkcolor=C["accent"],
                    thickness=10)
    style.configure("Success.Horizontal.TProgressbar",
                    troughcolor=C["bg_4"], background=C["success"],
                    bordercolor=C["bg_4"], lightcolor=C["success"], darkcolor=C["success"])

    # ── Treeview (game library, queue list) ──
    style.configure("Treeview",
                    background=C["bg_2"], fieldbackground=C["bg_2"],
                    foreground=C["fg_1"], bordercolor=C["bg_2"],
                    rowheight=28, font=F["body"], borderwidth=0)
    style.map("Treeview",
              background=[("selected", C["accent_15"])],
              foreground=[("selected", C["fg_0"])])
    style.configure("Treeview.Heading",
                    background=C["bg_4"], foreground=C["fg_3"],
                    relief="flat", borderwidth=0,
                    font=(_SANS, 9, "bold"), padding=(10, 7))
    style.map("Treeview.Heading",
              background=[("active", C["bg_5"])],
              foreground=[("active", C["accent"])])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # no border

    # Library variant — taller rows for cover art
    style.configure("Library.Treeview", rowheight=72, background=C["bg_2"])

    # ── Scrollbars ──
    style.configure("TScrollbar",
                    background=C["bg_4"], troughcolor=C["bg_1"],
                    bordercolor=C["bg_1"], arrowcolor=C["fg_4"],
                    relief="flat", borderwidth=0)
    style.map("TScrollbar",
              background=[("active", C["bg_5"]), ("pressed", C["accent_lo"])],
              arrowcolor=[("active", C["fg_1"])])
    style.configure("Vertical.TScrollbar", arrowsize=14)
    style.configure("Horizontal.TScrollbar", arrowsize=14)

    # ── Separator ──
    style.configure("TSeparator", background=C["border_2"])
    style.configure("Hairline.TSeparator", background=C["border_2"])

    # ── Spinbox ──
    style.configure("TSpinbox",
                    fieldbackground=C["bg_4"], foreground=C["fg_1"],
                    background=C["bg_4"], arrowcolor=C["fg_3"],
                    bordercolor=C["border_3"], lightcolor=C["border_3"], darkcolor=C["border_3"],
                    insertcolor=C["accent"], padding=6, relief="flat")
    style.map("TSpinbox",
              bordercolor=[("focus", C["accent"])],
              arrowcolor=[("active", C["accent"])])

    # ── Scale (slider) ──
    style.configure("TScale",
                    background=C["bg_1"], troughcolor=C["bg_4"],
                    bordercolor=C["bg_4"], lightcolor=C["accent"], darkcolor=C["accent"])

    return style


# ────────────────────────────────────────────────────────────────────
# RESPONSIVE SCALING
# ────────────────────────────────────────────────────────────────────
# The layout is designed for a 780x760 client area. When the window is
# resized the type scale follows it inside a deliberately narrow band:
# ~90% at the minimum window size, ~125% when maximised. That keeps
# text comfortable on a large monitor while ensuring fixed rows, sidebar
# labels and toolbar buttons never lose their captions.
#
# Fonts reach widgets two ways, so both are covered:
#   * ttk widgets inherit their font from a style; the style table is
#     rewritten from the same FONTS tokens (still the single source of
#     truth for the type scale).
#   * plain tk widgets store explicit font tuples; the widget tree is
#     walked and every font/wraplength is rescaled from the value it had
#     before scaling (remembered on the widget), so repeated resizes can
#     never compound the factor. The same pass scales explicit pixel
#     width/height on tk.Frame containers (tiles, columns, rails) so a
#     scaled caption cannot clip inside a container frozen at 100%.
#
# A <Map> hook rescales dialogs and lazily-built tabs created after a
# resize as soon as they appear.

_UI_SCALE_MIN   = 0.90
_UI_SCALE_MAX   = 1.25
_FONT_MIN_PT    = 7
_MIN_SCALED_PX  = 16

# Styles that pin a font in apply_theme(). Styles not listed here inherit
# their font from "." and need no separate update.
_STYLE_FONTS = {
    ".":                     "body",
    "TLabelframe.Label":     "h3",
    "Card.TLabelframe.Label": "h3",
    "TLabel":                "body",
    "H1.TLabel":             "h1",
    "H2.TLabel":             "h2",
    "H3.TLabel":             "h3",
    "Eyebrow.TLabel":        "eyebrow",
    "Body.TLabel":           "body",
    "Muted.TLabel":          "body",
    "Meta.TLabel":           "meta",
    "Mono.TLabel":           "mono",
    "Accent.TLabel":         "body_b",
    "Success.TLabel":        "body",
    "Warn.TLabel":           "body",
    "Danger.TLabel":         "body",
    "OnCard.H3.TLabel":      "h3",
    "TButton":               "button",
    "Primary.TButton":       "button",
    "Secondary.TButton":     "button",
    "Ghost.TButton":         "button",
    "Warn.TButton":          "body_b",
    "Danger.TButton":        "body_b",
    "Success.TButton":       "body_b",
    "Backport.TButton":      "body_b",
    "TCheckbutton":          "body",
    "OnCard.TCheckbutton":   "body",
    "TNotebook.Tab":         "tab",
    "Treeview":              "body",
    "Treeview.Heading":      "eyebrow",
    # Page-local table styles (configured in ui/tab_files.py and
    # ui/tab_ffpkg_edit.py) so their rows scale with their text too.
    "FileMgr.Treeview":          "mono",
    "FileMgr.Treeview.Heading":  "eyebrow",
    "FfpkgEdit.Treeview":        "mono",
    "FfpkgEdit.Treeview.Heading": "eyebrow",
}

# Padding that belongs to the type scale. Kept at the same values as
# apply_theme() so a resize is the only thing that changes them.
_STYLE_PADDING = {
    "TButton":          (14, 7),
    "Primary.TButton":  (16, 8),
    "Secondary.TButton": (14, 7),
    "Ghost.TButton":    (10, 6),
    "Warn.TButton":     (14, 7),
    "Danger.TButton":   (14, 7),
    "Success.TButton":  (14, 7),
    "Backport.TButton": (14, 7),
    "TNotebook.Tab":    (16, 9),
    "Treeview.Heading": (10, 7),
    "TEntry":           6,
    "Dark.TEntry":      6,
    "TCombobox":        6,
    "TSpinbox":         6,
    "Card.TLabelframe": 16,
}

# Base row heights keyed by style, with the floor used at the smallest
# scale. Row heights must follow the font or rows clip their own text.
_STYLE_ROWHEIGHTS = {
    "Treeview":             (28, 20),
    "Library.Treeview":     (72, 48),
    "FileMgr.Treeview":     (22, 16),
    "FfpkgEdit.Treeview":   (22, 16),
}

_ACTIVE_UI_SCALE = 1.0


def compute_ui_scale(width, height, design_width=780, design_height=760,
                     min_scale=_UI_SCALE_MIN, max_scale=_UI_SCALE_MAX):
    """Return the clamped type-scale factor for a client area.

    The smaller of the width/height ratios is used, so a very wide but
    short window never inflates text beyond the vertical space it has.
    Returns 1.0 for an unmapped/unknown size.
    """
    try:
        w = float(width)
        h = float(height)
        dw = max(1.0, float(design_width))
        dh = max(1.0, float(design_height))
    except (TypeError, ValueError):
        return 1.0
    if w <= 1 or h <= 1:
        return 1.0
    factor = min(w / dw, h / dh)
    return max(float(min_scale), min(float(max_scale), factor))


def _scale_font_spec(spec, factor):
    """Scale a (family, size, *styles) tuple, never below _FONT_MIN_PT."""
    try:
        family = spec[0]
        size = int(spec[1])
        rest = tuple(spec[2:])
    except (TypeError, ValueError, IndexError):
        return spec
    return (family, max(_FONT_MIN_PT, int(size * factor + 0.5))) + rest


def set_scaled_font(widget, base_spec, factor=None):
    """Configure `widget` with `base_spec` at the current scale.

    Use this where a font is assigned *after* startup (active/inactive
    state changes, drop-zone glyph resets, cover placeholders). Besides
    looking right immediately, it updates the scaler's saved base, so a
    later window resize cannot mistake the scaled value for a new base
    and compound the factor.
    """
    if factor is None:
        factor = _ACTIVE_UI_SCALE
    try:
        factor = float(factor)
    except (TypeError, ValueError):
        factor = 1.0
    scaled = _scale_font_spec(base_spec, factor)
    try:
        widget.configure(font=scaled)
    except tk.TclError:
        return
    if isinstance(base_spec, (tuple, list)):
        try:
            widget._ui_scale_font_base = tuple(base_spec)
            widget._ui_scale_font_key = _font_key(scaled)
        except (TypeError, ValueError, IndexError):
            pass


def set_scaled_dimension(widget, option, base_value, factor=None):
    """Set an explicit pixel width/height at the current scale.

    Use this where layout code changes a fixed container (a collapsed
    sidebar rail, a resized column) after startup. It records the value
    as the 100% base, so the next window resize scales from the design
    size instead of treating the current scaled width as a new base.
    """
    if factor is None:
        factor = _ACTIVE_UI_SCALE
    try:
        factor = float(factor)
        base = int(base_value)
    except (TypeError, ValueError):
        return
    if base < 1:
        return
    scaled = max(1, int(base * factor + 0.5))
    try:
        widget.configure(**{option: scaled})
    except tk.TclError:
        return
    setattr(widget, "_ui_scale_%s_base" % option, base)
    setattr(widget, "_ui_scale_%s_applied" % option, scaled)


def _scale_padding(value, factor):
    """Scale an int or (x, y) ttk padding tuple."""
    if isinstance(value, (tuple, list)):
        return tuple(max(1, int(v * factor + 0.5)) for v in value)
    return max(1, int(value * factor + 0.5))


def _parse_font_spec(widget, value):
    """Parse a widget font option into a tuple, or None if it is unusable.

    Named fonts (a single token such as "TkDefaultFont") are skipped:
    they are shared, so rescaling them per widget would double-apply.
    Pixel fonts (negative sizes) are intentional and left alone.
    """
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (tuple, list)):
            parts = tuple(str(p) for p in value)
        else:
            parts = widget.tk.splitlist(str(value))
    except (tk.TclError, ValueError):
        return None
    if len(parts) < 2:
        return None
    try:
        size = int(float(parts[1]))
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None
    return (parts[0], size) + tuple(parts[2:])


def _font_key(parts):
    """Normalised comparison key so Tk's reserialisation of a font does
    not look like a user-initiated change (e.g. "normal" dropped)."""
    styles = tuple(sorted(
        str(p).lower() for p in parts[2:]
        if str(p).lower() not in ("normal", "roman", "regular")))
    return (str(parts[0]).lower(), int(parts[1]), styles)


def _rescale_toplevel_geometry(win, factor):
    """Scale a fixed-size dialog window with the type scale.

    Only windows the user cannot resize are touched. Auto-sized dialogs
    already grow with their scaled content, and user-resizable editors
    must keep the size the user chose. Position is left to the window
    manager (geometry with size only does not move the window).
    """
    try:
        # Call Tcl directly: wm resizable takes an optional size, and this
        # form is unambiguous across tkinter versions (returns "0 0").
        flags = win.tk.splitlist(win.tk.call('wm', 'resizable', str(win)))
        if any(int(f) for f in flags):
            return
        # Not shown yet: leave the geometry for the <Map> hook, which runs
        # once the window has rendered and reports a real size.
        if not win.winfo_ismapped():
            return
    except (TypeError, ValueError, tk.TclError):
        return
    try:
        width = win.winfo_width()
        height = win.winfo_height()
    except tk.TclError:
        return
    if width <= 1 or height <= 1:
        return

    try:
        factor_prev = float(getattr(win, "_ui_scale_geom_factor", 1.0))
    except (TypeError, ValueError):
        factor_prev = 1.0
    if factor_prev <= 0:
        factor_prev = 1.0
    base = getattr(win, "_ui_scale_geom_base", None)
    applied = getattr(win, "_ui_scale_geom_applied", None)
    if base is None:
        base = (width, height)          # first sight: assume 100% size
    elif applied != (width, height):
        # The app changed the size while the type was at factor_prev.
        # Divide back to the 100% size instead of making the already
        # scaled size the new base, which would compound on next resize.
        base = (max(1, int(width / factor_prev + 0.5)),
                max(1, int(height / factor_prev + 0.5)))
    new_w = max(1, int(base[0] * factor + 0.5))
    new_h = max(1, int(base[1] * factor + 0.5))
    try:
        # Never push a dialog off small screens.
        new_w = min(new_w, max(320, win.winfo_screenwidth() - 60))
        new_h = min(new_h, max(240, win.winfo_screenheight() - 100))
    except tk.TclError:
        pass
    applied_ok = True
    if (new_w, new_h) != (width, height):
        try:
            win.geometry("%dx%d" % (new_w, new_h))
        except tk.TclError:
            new_w, new_h = width, height
            applied_ok = False
    win._ui_scale_geom_base = base
    win._ui_scale_geom_applied = (new_w, new_h)
    if applied_ok:
        win._ui_scale_geom_factor = factor


def _rescale_widget(widget, factor):
    """Rescale one widget's explicit font and wraplength, idempotently.

    The pre-scale value is stored on the widget and reused on every
    subsequent call, so dragging the window back and forth cannot
    accumulate the factor. If application code assigns a *new* font at
    runtime, the change is detected and becomes the new base.
    """
    try:
        raw = widget.cget("font")
    except tk.TclError:
        raw = None
    specs = _parse_font_spec(widget, raw) if raw else None
    if specs is not None:
        key = _font_key(specs)
        base = getattr(widget, "_ui_scale_font_base", None)
        applied = getattr(widget, "_ui_scale_font_key", None)
        if base is None or applied != key:
            base = specs                 # first sight, or changed by the app
        new = _scale_font_spec(base, factor)
        new_key = _font_key(new)
        if new_key != key:
            try:
                widget.configure(font=new)
            except tk.TclError:
                new_key = key
        widget._ui_scale_font_base = base
        widget._ui_scale_font_key = new_key

    try:
        wrap = int(widget.cget("wraplength"))
    except (tk.TclError, TypeError, ValueError):
        wrap = 0
    if wrap > 0:
        base = getattr(widget, "_ui_scale_wrap_base", None)
        applied = getattr(widget, "_ui_scale_wrap_applied", None)
        if base is None or applied != wrap:
            base = wrap
        new = max(1, int(base * factor + 0.5))
        if new != wrap:
            try:
                widget.configure(wraplength=new)
            except tk.TclError:
                new = wrap
        widget._ui_scale_wrap_base = base
        widget._ui_scale_wrap_applied = new

    # Fixed-size dialogs: their content is scaled through the global ttk
    # styles, so a non-resizable window sized for 100% type would clip it.
    if isinstance(widget, tk.Toplevel):
        _rescale_toplevel_geometry(widget, factor)
        return

    # Fixed-size tk.Frame containers (icon tiles, definition columns,
    # sidebar rails, spacers). Frame width/height are pixels and default
    # to 0, so any non-trivial value is one the UI set deliberately.
    # Canvas is left alone: its defaults are non-zero and most canvases
    # here are geometry-managed rather than text containers. Hairlines and
    # small dots (< 16 px) keep their exact pixel size.
    if not isinstance(widget, tk.Frame):
        return
    for opt in ("width", "height"):
        try:
            current = int(widget.cget(opt))
        except (tk.TclError, TypeError, ValueError):
            continue
        if current < _MIN_SCALED_PX:
            continue
        base_attr = "_ui_scale_%s_base" % opt
        applied_attr = "_ui_scale_%s_applied" % opt
        base = getattr(widget, base_attr, None)
        applied = getattr(widget, applied_attr, None)
        if base is None or applied != current:
            base = current
        new = max(1, int(base * factor + 0.5))
        if new != current:
            try:
                widget.configure(**{opt: new})
            except tk.TclError:
                new = current
        setattr(widget, base_attr, base)
        setattr(widget, applied_attr, new)


def _walk_and_rescale(root, factor):
    """Walk the whole widget tree (including Toplevels) and rescale."""
    stack = [root]
    while stack:
        widget = stack.pop()
        try:
            _rescale_widget(widget, factor)
        except (tk.TclError, RuntimeError):
            pass
        # A dialog that has never been mapped has not rendered yet. Leave
        # its subtree at base size; the <Map> hook scales it when it is
        # first shown, so the geometry read there is the unscaled natural
        # size rather than a value that was already scaled once.
        if widget is not root and isinstance(widget, tk.Toplevel):
            try:
                if not widget.winfo_ismapped():
                    continue
            except tk.TclError:
                continue
        try:
            stack.extend(widget.winfo_children())
        except tk.TclError:
            pass


def _apply_style_scale(style, factor):
    """Rewrite ttk fonts/padding and metric values for `factor`."""
    for name, token in _STYLE_FONTS.items():
        spec = FONTS.get(token)
        if not spec:
            continue
        try:
            style.configure(name, font=_scale_font_spec(spec, factor))
        except tk.TclError:
            pass
    for name, pad in _STYLE_PADDING.items():
        try:
            style.configure(name, padding=_scale_padding(pad, factor))
        except tk.TclError:
            pass
    for name, (base, floor) in _STYLE_ROWHEIGHTS.items():
        try:
            style.configure(name, rowheight=max(floor, int(base * factor + 0.5)))
        except tk.TclError:
            pass


def apply_ui_scale(root, factor, force=False):
    """Apply `factor` to ttk styles and every explicit tk font/wraplength.

    No-op when the factor is unchanged (or when scaling was never
    installed on this root), which keeps repeated Configure events cheap.
    `force` re-applies the same factor — used after a runtime UI rebuild
    that recreated widgets and page-local ttk styles.
    """
    state = getattr(root, "_ui_scale_state", None)
    if state is None:
        return
    try:
        factor = float(factor)
    except (TypeError, ValueError):
        return
    factor = max(state["min"], min(state["max"], factor))
    if not force and abs(factor - state["factor"]) < 0.002:
        return
    state["factor"] = factor

    global _ACTIVE_UI_SCALE
    _ACTIVE_UI_SCALE = factor

    try:
        style = ttk.Style(root)
    except (tk.TclError, RuntimeError):
        style = None
    if style is not None:
        _apply_style_scale(style, factor)

    # This option targets Tk's *internal* combobox popdown listbox, not a
    # Python widget in the tree, so it cannot be double-scaled by the walk.
    try:
        root.option_add("*TCombobox*Listbox.font",
                        _scale_font_spec(FONTS["body"], factor))
    except tk.TclError:
        pass

    _walk_and_rescale(root, factor)


def refresh_responsive_scaling(root):
    """Re-apply the current factor after rebuilding UI at runtime.

    A language change recreates tab widgets *and* re-runs page-local ttk
    style setup (table fonts/row heights) at base size, so silently
    re-applying the existing factor would leave those pieces behind.
    """
    state = getattr(root, "_ui_scale_state", None)
    if state is None:
        return
    apply_ui_scale(root, state["factor"], force=True)


def install_responsive_scaling(root, design_width=780, design_height=760,
                               min_scale=_UI_SCALE_MIN,
                               max_scale=_UI_SCALE_MAX, debounce_ms=140):
    """Make type scale with the window.

    Installs one debounced <Configure> handler on the root (so drag-resize
    costs nothing until the user pauses) and a <Map> rescue hook that
    scales dialogs and lazily-built tab contents created afterwards.
    Safe to call twice: the configuration is updated, not stacked.
    """
    state = getattr(root, "_ui_scale_state", None)
    if state is not None:
        state.update(design_w=float(design_width),
                     design_h=float(design_height),
                     min=float(min_scale), max=float(max_scale),
                     debounce=int(debounce_ms))
        return

    state = {
        "factor": 1.0,
        "after_id": None,
        "design_w": float(design_width),
        "design_h": float(design_height),
        "min": float(min_scale),
        "max": float(max_scale),
        "debounce": int(debounce_ms),
    }
    root._ui_scale_state = state

    def _apply_from_geometry():
        state["after_id"] = None
        try:
            width = root.winfo_width()
            height = root.winfo_height()
        except tk.TclError:
            return
        factor = compute_ui_scale(width, height,
                                  state["design_w"], state["design_h"],
                                  state["min"], state["max"])
        apply_ui_scale(root, factor)

    def _on_configure(event):
        # The toplevel bindtag also receives events from every child, so
        # only react to the window itself changing size.
        if event.widget is not root:
            return
        if state["after_id"] is not None:
            try:
                root.after_cancel(state["after_id"])
            except (tk.TclError, ValueError):
                pass
        state["after_id"] = root.after(state["debounce"], _apply_from_geometry)

    def _on_map(event):
        # Newly created widgets (dialogs, lazy tabs) arrive unscaled.
        if abs(state["factor"] - 1.0) < 0.002:
            return
        try:
            _rescale_widget(event.widget, state["factor"])
        except (tk.TclError, RuntimeError):
            pass

    root.bind("<Configure>", _on_configure, add="+")
    root.bind_all("<Map>", _on_map, add="+")

    # Catch a window restored at a larger size before it is mapped.
    try:
        root.after_idle(_apply_from_geometry)
    except tk.TclError:
        pass


# ────────────────────────────────────────────────────────────────────
# CONVENIENCE WIDGET FACTORIES
# Use these instead of raw tk.* widgets for consistent look without
# remembering style names.
# ────────────────────────────────────────────────────────────────────
def make_card(parent: tk.Widget, **kwargs) -> ttk.Frame:
    """A bordered card surface (bg_2)."""
    f = ttk.Frame(parent, style="Card.TFrame", padding=16, **kwargs)
    return f


def make_callout(parent: tk.Widget, kind: str = "info", text: str = "") -> tk.Frame:
    """
    A callout box (info / warn / danger / success) — left-bordered tinted strip.
    Uses raw tk.Frame because ttk doesn't expose a left-only border. Match the
    .info / .warn / .danger / .success classes in the design system.
    """
    palette = {
        "info":    (COLORS["info_bg"],    COLORS["accent"],     COLORS["accent_hi"]),
        "warn":    (COLORS["warn_bg"],    COLORS["warn"],       COLORS["warn_hi"]),
        "danger":  (COLORS["danger_bg"],  COLORS["danger"],     COLORS["danger_hi"]),
        "success": (COLORS["success_bg"], COLORS["success"],    COLORS["success_hi"]),
    }
    bg, accent_color, fg = palette.get(kind, palette["info"])

    wrap = tk.Frame(parent, bg=accent_color)                 # left strip = accent
    inner = tk.Frame(wrap, bg=bg, padx=14, pady=10)
    inner.pack(side="right", fill="both", expand=True, padx=(3, 0))
    if text:
        tk.Label(inner, text=text, bg=bg, fg=fg,
                 font=FONTS["body"], anchor="w", justify="left",
                 wraplength=560).pack(anchor="w")
    return wrap


def make_status_pill(parent: tk.Widget, kind: str, text: str) -> tk.Label:
    """A rounded-feel status pill. tk doesn't do real rounded corners,
    so this is a subtly tinted label — looks correct in the dark UI."""
    palette = {
        "ok":      (COLORS["success_bg"], COLORS["success_hi"]),
        "active":  (COLORS["accent_08"],  COLORS["accent_hi"]),
        "wait":    (COLORS["bg_3"],       COLORS["fg_5"]),
        "warn":    (COLORS["warn_bg"],    COLORS["warn_hi"]),
        "fail":    (COLORS["danger_bg"],  COLORS["danger_hi"]),
    }
    bg, fg = palette.get(kind, palette["wait"])
    return tk.Label(parent, text=f" {text} ", bg=bg, fg=fg,
                    font=(_SANS, 9, "bold"), padx=8, pady=2, bd=0)


def make_titlebar(parent: tk.Widget, title: str, version: str = "") -> ttk.Frame:
    """The app's top header strip: brand rule + title + version.

    Uses a slim blue rule instead of an emoji/icon tile — the same
    navigation language as the page headers.
    """
    bar = ttk.Frame(parent, style="Card.TFrame", padding=(20, 14))
    bar.pack(fill="x")
    rule = tk.Frame(bar, bg=COLORS["accent"], width=3, height=36)
    rule.pack(side="left", fill="y")
    title_frame = ttk.Frame(bar, style="Card.TFrame")
    title_frame.pack(side="left", padx=(12, 0))
    ttk.Label(title_frame, text=title, style="OnCard.H3.TLabel",
              font=(_SANS, 13, "bold")).pack(anchor="w")
    if version:
        ttk.Label(title_frame, text=f"v{version}",
                  style="OnCard.Muted.TLabel",
                  font=FONTS["meta"]).pack(anchor="w")
    return bar


# ════════════════════════════════════════════════════════════════════
# STAGE 1 — DESIGN-TOKEN SYSTEM  (added 2026-05, UI refactor)
# ════════════════════════════════════════════════════════════════════
# Everything below this banner is ADDITIVE. No constant above this line
# is changed or removed. All existing imports
# (`apply_theme`, `COLORS`, `FONTS`, `make_card`, `make_callout`,
# `make_status_pill`, `make_titlebar`) keep working exactly as before.
#
# These tokens are NOT yet wired into any page. They exist so later
# stages can build reusable components against one source of truth.
# The app launches and behaves identically with this block present.
# ════════════════════════════════════════════════════════════════════

# ── SPACING ──────────────────────────────────────────────────────────
# A 4px base scale. Use SPACING["md"] etc. instead of magic numbers so
# padding stays consistent across the redesigned UI.
SPACING = {
    "none": 0,
    "xxs":  2,
    "xs":   4,
    "sm":   8,
    "md":   12,
    "lg":   16,
    "xl":   20,
    "xxl":  24,
    "xxxl": 32,
    "huge": 48,
}

# ── RADIUS ───────────────────────────────────────────────────────────
# Tkinter widgets cannot truly round their corners; these values are for
# Canvas-drawn rounded rectangles in later component work. Kept here so
# the "roundedness" of the UI is defined in one place.
RADIUS = {
    "none": 0,
    "sm":   4,
    "md":   8,
    "lg":   12,
    "xl":   16,
    "pill": 999,
}

# ── ELEVATION / BORDER STYLES ────────────────────────────────────────
# Tk has no drop-shadow; "elevation" here is expressed as a background +
# border pairing. Each level names a (background-token, border-token).
ELEVATION = {
    "flat":    {"bg": "bg_1", "border": "border_1"},
    "raised":  {"bg": "bg_2", "border": "border_2"},
    "overlay": {"bg": "bg_3", "border": "border_3"},
    "popover": {"bg": "bg_4", "border": "border_4"},
}

BORDERS = {
    "hairline":  {"color": "border_2", "width": 1},
    "card":      {"color": "border_3", "width": 1},
    "strong":    {"color": "border_4", "width": 1},
    "accent":    {"color": "accent",   "width": 1},
    "focus":     {"color": "accent",   "width": 2},
}

# ── SEMANTIC / STATUS COLORS ─────────────────────────────────────────
# Maps an app-level status word to a (text, background, border) trio of
# EXISTING color-token names. Used by apply_status_badge_style and by
# later badge components. Values are token names, resolved via get_color.
STATUS_COLORS = {
    "idle":     {"fg": "fg_5",       "bg": "bg_3",        "border": "border_3"},
    "waiting":  {"fg": "fg_5",       "bg": "bg_3",        "border": "border_3"},
    "queued":   {"fg": "fg_4",       "bg": "bg_3",        "border": "border_3"},
    "running":  {"fg": "accent_hi",  "bg": "accent_08",   "border": "accent"},
    "active":   {"fg": "accent_hi",  "bg": "accent_08",   "border": "accent"},
    "progress": {"fg": "accent_hi",  "bg": "accent_08",   "border": "accent"},
    "success":  {"fg": "success_hi", "bg": "success_bg",  "border": "success"},
    "done":     {"fg": "success_hi", "bg": "success_bg",  "border": "success"},
    "ok":       {"fg": "success_hi", "bg": "success_bg",  "border": "success"},
    "warn":     {"fg": "warn_hi",    "bg": "warn_bg",     "border": "warn"},
    "warning":  {"fg": "warn_hi",    "bg": "warn_bg",     "border": "warn"},
    "error":    {"fg": "danger_hi",  "bg": "danger_bg",   "border": "danger"},
    "failed":   {"fg": "danger_hi",  "bg": "danger_bg",   "border": "danger"},
    "fail":     {"fg": "danger_hi",  "bg": "danger_bg",   "border": "danger"},
}

# ── BUTTON STYLES ────────────────────────────────────────────────────
# Maps a variant name to the EXISTING ttk style string already defined
# in apply_theme(). Nothing new is registered with ttk — this is just a
# lookup so components can ask for "primary" without knowing the exact
# ttk style name.
BUTTON_STYLES = {
    "default":   "TButton",
    "primary":   "Primary.TButton",
    "secondary": "Secondary.TButton",
    "ghost":     "Ghost.TButton",
    "warn":      "Warn.TButton",
    "danger":    "Danger.TButton",
    "success":   "Success.TButton",
    "backport":  "Backport.TButton",
    "purple":    "Backport.TButton",   # alias — purple == backport accent
}

# ── CARD STYLES ──────────────────────────────────────────────────────
# Named card surfaces → (background-token, border-token, default padding).
CARD_STYLES = {
    "default":  {"bg": "bg_2", "border": "border_3", "pad": SPACING["lg"]},
    "flat":     {"bg": "bg_1", "border": "border_2", "pad": SPACING["md"]},
    "raised":   {"bg": "bg_3", "border": "border_3", "pad": SPACING["lg"]},
    "inset":    {"bg": "bg_0", "border": "border_2", "pad": SPACING["md"]},
    "accent":   {"bg": "bg_2", "border": "accent",   "pad": SPACING["lg"]},
}

# ── INPUT STYLES ─────────────────────────────────────────────────────
# Named input surfaces → token set + the matching ttk style for ttk
# entries/combos. Raw tk widgets use the color tokens directly.
INPUT_STYLES = {
    "default": {"bg": "field_bg", "fg": "field_fg", "border": "border_3",
                "focus": "accent", "ttk_entry": "TEntry"},
    "dark":    {"bg": "bg_4",     "fg": "fg_1",      "border": "border_3",
                "focus": "accent", "ttk_entry": "Dark.TEntry"},
}

# ── LOG COLORS ───────────────────────────────────────────────────────
# Colors for live-log / console text by line severity. Resolved to hex
# via get_color. Used by the log-view component in a later stage.
LOG_COLORS = {
    "bg":       "bg_0",
    "default":  "fg_1",
    "dim":      "fg_4",
    "info":     "accent_hi",
    "success":  "success_hi",
    "warn":     "warn_hi",
    "error":    "danger_hi",
    "command":  "teal_hi",
    "phosphor": "success_ok",   # klog CRT-green
}


# ── SAFE HELPER FUNCTIONS ────────────────────────────────────────────
# All helpers are defensive: bad input never raises, it returns a
# sensible fallback. Wiring them into a widget is harmless because the
# worst case is a no-op.

def get_color(name, fallback=None):
    """Resolve a color token to its hex value.

    `name` may be a key in COLORS or in STATUS_COLORS. Unknown names
    return `fallback` (or COLORS['fg_1'] if no fallback given). Never
    raises.
    """
    try:
        if name in COLORS:
            return COLORS[name]
    except Exception:
        pass
    if fallback is not None:
        # fallback may itself be a token name — resolve one level.
        return COLORS.get(fallback, fallback)
    return COLORS.get("fg_1", "#F5F7FA")


def get_font(name, fallback=None):
    """Resolve a font token to its (family, size, weight) tuple.

    Unknown names return `fallback` if it is a known token, else the
    fallback tuple as-is, else FONTS['body']. Never raises.
    """
    try:
        if name in FONTS:
            return FONTS[name]
    except Exception:
        pass
    if fallback is not None:
        if isinstance(fallback, str) and fallback in FONTS:
            return FONTS[fallback]
        return fallback
    return FONTS.get("body", (_SANS, 10, "normal"))


def get_status_color(status, role="fg"):
    """Resolve a STATUS_COLORS entry to a hex value.

    `role` is one of 'fg', 'bg', 'border'. Unknown status falls back to
    'idle'. Never raises.
    """
    entry = STATUS_COLORS.get(str(status).lower(), STATUS_COLORS["idle"])
    token = entry.get(role, entry.get("fg"))
    return get_color(token)


def apply_card_style(widget, variant="default"):
    """Style an existing tk.Frame (or tk.Widget) as a card surface.

    Only applies to plain tk widgets that accept bg/highlight options;
    ttk widgets are left untouched (they should use the 'Card.TFrame'
    ttk style instead). Returns the widget for chaining. Never raises.
    """
    spec = CARD_STYLES.get(variant, CARD_STYLES["default"])
    try:
        widget.configure(
            bg=get_color(spec["bg"]),
            highlightbackground=get_color(spec["border"]),
            highlightcolor=get_color(spec["border"]),
            highlightthickness=1,
            bd=0,
        )
    except Exception:
        # ttk widget or option not supported — no-op, safe.
        pass
    return widget


def apply_button_style(widget, variant="default"):
    """Apply a button variant to a widget.

    For a ttk.Button, sets the matching ttk style string. For a plain
    tk.Button, applies a token-based color approximation. Returns the
    widget. Never raises.
    """
    ttk_style = BUTTON_STYLES.get(variant, BUTTON_STYLES["default"])
    # ttk path
    try:
        if isinstance(widget, ttk.Widget):
            widget.configure(style=ttk_style)
            return widget
    except Exception:
        pass
    # plain tk.Button path — approximate with token colors
    _tk_btn_palette = {
        "default":   ("bg_4",   "fg_1"),
        "primary":   ("accent", "fg_0"),
        "secondary": ("bg_4",   "accent"),
        "ghost":     ("bg_1",   "fg_3"),
        "warn":      ("warn",   "bg_0"),
        "danger":    ("danger", "bg_0"),
        "success":   ("success", "bg_0"),
        "backport":  ("purple", "fg_0"),
        "purple":    ("purple", "fg_0"),
    }
    bg_tok, fg_tok = _tk_btn_palette.get(variant, _tk_btn_palette["default"])
    try:
        widget.configure(
            bg=get_color(bg_tok), fg=get_color(fg_tok),
            activebackground=get_color(bg_tok),
            activeforeground=get_color(fg_tok),
            relief="flat", bd=0, font=get_font("button"),
            highlightthickness=0, cursor="hand2",
        )
    except Exception:
        pass
    return widget


def apply_input_style(widget, variant="default"):
    """Style an input widget (tk.Entry / ttk.Entry / tk.Text).

    ttk entries/combos get the matching ttk style; plain tk inputs get
    token colors. Returns the widget. Never raises.
    """
    spec = INPUT_STYLES.get(variant, INPUT_STYLES["default"])
    # ttk path
    try:
        if isinstance(widget, ttk.Widget):
            widget.configure(style=spec["ttk_entry"])
            return widget
    except Exception:
        pass
    # plain tk path
    try:
        widget.configure(
            bg=get_color(spec["bg"]),
            fg=get_color(spec["fg"]),
            insertbackground=get_color(spec["focus"]),
            highlightbackground=get_color(spec["border"]),
            highlightcolor=get_color(spec["focus"]),
            highlightthickness=1,
            relief="flat", bd=0,
        )
    except Exception:
        pass
    return widget


def apply_status_badge_style(widget, status):
    """Style a tk.Label (or similar) as a status badge.

    Uses STATUS_COLORS to set fg/bg. Intended for plain tk.Label badges.
    Returns the widget. Never raises.
    """
    try:
        widget.configure(
            bg=get_status_color(status, "bg"),
            fg=get_status_color(status, "fg"),
            font=get_font("eyebrow"),
            padx=SPACING["sm"], pady=SPACING["xxs"],
            bd=0, highlightthickness=0,
        )
    except Exception:
        pass
    return widget


# ── DESIGN-TOKEN SELF-TEST ───────────────────────────────────────────
# Optional sanity check; not run on import. Call tokens_selftest() in a
# REPL to confirm every token table resolves cleanly.
def tokens_selftest():
    """Return True if all token tables are internally consistent."""
    ok = True
    for tbl in (CARD_STYLES, INPUT_STYLES):
        for _name, spec in tbl.items():
            for key in ("bg", "border"):
                if key in spec and spec[key] not in COLORS:
                    print("MISSING color token:", spec[key]); ok = False
    for _s, spec in STATUS_COLORS.items():
        for role in ("fg", "bg", "border"):
            if spec[role] not in COLORS:
                print("MISSING status token:", spec[role]); ok = False
    for tok in LOG_COLORS.values():
        if tok not in COLORS:
            print("MISSING log token:", tok); ok = False
    for _v, st in BUTTON_STYLES.items():
        if not isinstance(st, str):
            print("BAD button style:", st); ok = False
    return ok


# ────────────────────────────────────────────────────────────────────
# DEMO — run this file directly to see every styled component
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("980x720")
    root.title("exFAT Image Builder — theme preview")
    apply_theme(root)

    make_titlebar(root, "exFAT Image Builder", "1.9.0")

    main = ttk.Frame(root, style="Surface.TFrame", padding=20)
    main.pack(fill="both", expand=True)

    nb = ttk.Notebook(main)
    nb.pack(fill="both", expand=True)

    for label in ("exFAT", "ffpkg", "Library", "My Images",
                  "Klog", "Settings"):
        page = ttk.Frame(nb, style="Surface.TFrame", padding=20)
        nb.add(page, text=label)

    page = nb.nametowidget(nb.tabs()[0])

    card = make_card(page); card.pack(fill="x", pady=(0, 12))
    ttk.Label(card, text="Build a new image", style="OnCard.H3.TLabel").pack(anchor="w")
    ttk.Label(card, text="Source folder must contain eboot.bin",
              style="OnCard.Muted.TLabel").pack(anchor="w", pady=(2, 12))

    row = ttk.Frame(card, style="Card.TFrame"); row.pack(fill="x", pady=4)
    ttk.Label(row, text="Game folder", style="OnCard.TLabel", width=14).pack(side="left")
    ttk.Entry(row).pack(side="left", fill="x", expand=True, padx=(0, 8))
    ttk.Button(row, text="Browse…", style="Secondary.TButton").pack(side="left")

    btnrow = ttk.Frame(card, style="Card.TFrame"); btnrow.pack(fill="x", pady=(16, 0))
    ttk.Button(btnrow, text="Add to Queue", style="Primary.TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btnrow, text="Build All",    style="Success.TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btnrow, text="Pause",        style="Secondary.TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btnrow, text="Backport",     style="Backport.TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btnrow, text="Cancel",       style="Ghost.TButton").pack(side="right")

    make_callout(page, "info",
        "Sector size is locked at 512 bytes — required for PS5 compatibility."
        ).pack(fill="x", pady=4)
    make_callout(page, "warn",
        "Output folder must NOT be inside the game folder."
        ).pack(fill="x", pady=4)
    make_callout(page, "danger",
        "Post-build deletion of source folder cannot be undone."
        ).pack(fill="x", pady=4)
    make_callout(page, "success",
        "Build complete · 12.4 GB · verified."
        ).pack(fill="x", pady=4)

    pb_card = make_card(page); pb_card.pack(fill="x", pady=(12, 0))
    ttk.Label(pb_card, text="Build progress", style="OnCard.H3.TLabel").pack(anchor="w")
    pb = ttk.Progressbar(pb_card, style="Build.Horizontal.TProgressbar",
                         mode="determinate", value=63)
    pb.pack(fill="x", pady=(8, 4))

    pillrow = ttk.Frame(pb_card, style="Card.TFrame"); pillrow.pack(anchor="w", pady=(8, 0))
    for kind, text in (("ok", "Mount"), ("ok", "Format"),
                       ("active", "Copy 63%"), ("wait", "Verify")):
        make_status_pill(pillrow, kind, text).pack(side="left", padx=(0, 6))

    root.mainloop()
