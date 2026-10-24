# 🎮 exFAT Image Builder

**The Ultimate Windows Toolkit for Building, Editing & Backporting PS5
Game Images**

Build • Edit • Convert • Backport • Deploy

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![License](https://img.shields.io/github/license/kerrdec97/ps5-exfat-builder)
![Release](https://img.shields.io/github/v/release/kerrdec97/ps5-exfat-builder)
![Downloads](https://img.shields.io/github/downloads/kerrdec97/ps5-exfat-builder/total)
![Build](https://github.com/kerrdec97/ps5-exfat-builder/actions/workflows/build-release.yml/badge.svg)


------------------------------------------------------------------------

## 🚀 Overview

**exFAT Image Builder** is an all-in-one Windows application for
creating, editing, converting and managing mountable PS5 game images
from your own game dumps.

Whether you're building an **exFAT image**, generating a **compressed
FFPFSC**, creating an **FFPKG**, applying **backports**, managing
**DLC**, or transferring directly to your PS5, everything is available
from one modern interface.

Designed for speed, reliability and ease of use.

> ⚠️ **Homebrew & Personal Backup Tool**
>
> This software is intended only for games and content **you legally own
> and have dumped yourself**.
>
> It **does not** download games, decrypt retail packages, bypass DRM or
> provide copyrighted content.

------------------------------------------------------------------------

# ✨ Features

## 📦 Image Builder

-   ✅ Build exFAT Images
-   ✅ Build FFPKG (UFS2)
-   ✅ Build Compressed FFPFSC Images
-   ✅ Automatic Image Verification
-   ✅ Queue Multiple Builds
-   ✅ Automatic Game Detection
-   ✅ Custom output names (title, version, required firmware, title ID)

## 🛠 Image Editor

-   Replace Files
-   Add Files
-   Delete Files
-   Rebuild without recreating the entire image

## 🔥 Backport Toolkit

-   Auto Backport
-   SDK Detection
-   Fakelib Support
-   DLC Support
-   Language Stripper
-   Automatic AMPR Generation
-   Restore Original Files

## 🎮 PS5 Integration

-   FTP Browser
-   Remote Content Manager
-   Payload Sender
-   Live Kernel Log Viewer
-   Console Diagnostics
-   Direct PS5 Deployment

## 📚 Library

-   Automatic Cover Art
-   Metadata Detection
-   Bulk Rename
-   Batch Queue
-   Format Conversion
-   Game Browser

## 🌍 Languages

Supports **17 interface languages**, maintained by the community.

------------------------------------------------------------------------

# 📸 Screenshots

> Add screenshots of the Build, Backports, Library, FTP and Console
> Tools tabs here.

------------------------------------------------------------------------

# ⚡ Quick Start

1.  Install Windows 10/11, OSFMount and (.NET 8 for FFPKG).
2.  Open the **Build** tab.
3.  Select your PS5 game dump.
4.  Choose **exFAT**, **FFPKG** or **FFPFSC**.
5.  Click **Add to Queue** then **Build All**.
6.  Wait for Scan → Build → Copy → Verify to complete.

------------------------------------------------------------------------

# 🏷 Output File Naming

Automatic output names are controlled by a template in
**Settings → Build → Output file naming**, also reachable from the
**Edit template…** link in the Build tab's *Output name* card. The
default is:

```text
%PPSA% %TITLE% (%VERSION%) (%FIRMWARE%)
```

| Placeholder | Value |
| --- | --- |
| `%TITLE%` | Game title |
| `%VERSION%` | Game / patch version, e.g. `01.000.000` |
| `%FIRMWARE%` | Required system firmware, e.g. `10.00` or `12.70` |
| `%PPSA%` | Title ID, e.g. `PPSA01234` (aliases: `%TITLE_ID%`, `%TITLEID%`, `%ID%`) |
| `%FW%` | Alias for `%FIRMWARE%` |

Example using the default template:

```text
PPSA01234 Marvel's Spider-Man 2 (01.000.000) (10.00).exfat
```

A missing value removes that placeholder together with its brackets, so
a game with no detected firmware keeps the classic shape:

```text
PPSA01234 Some Game (01.000.000).exfat
```

Select the **Classic** preset to omit firmware entirely, or type any
arrangement of the placeholders above. The template applies to automatic
`.exfat` / `.ffpkg` names and to queue and UniBuild output. The required
firmware is read from `param.json`
(`requiredSystemSoftwareVersion`), with `param.sfo` as a fallback.

------------------------------------------------------------------------

# 🧱 Building from Source

See **[BUILD.md](BUILD.md)** for Windows prerequisites, manual build
steps, checksum generation, and the GitHub Actions build/release
pipeline.

------------------------------------------------------------------------

# 📦 Supported Formats

  Format     Description
  ---------- --------------------------
  📀 exFAT   Standard mountable image
  📦 FFPKG   UFS2 Image
  🗜 FFPFSC   Compressed PFS Image

------------------------------------------------------------------------

# ⭐ Why exFAT Image Builder?

-   Modern Windows Interface
-   Multiple Image Formats
-   Integrated Backport Engine
-   Automatic Metadata Detection
-   Built-in FTP Client
-   Queue System
-   Live Kernel Logs
-   DLC Support
-   Active Development

------------------------------------------------------------------------

# ❤️ Credits

Thanks to everyone in the PS5 Homebrew community, especially:

-   Nazky
-   BestPig
-   SvenGDK
-   drakmor
-   PSBrew
-   john-tornblom
-   ps5-payload-dev
-   idlesauce
-   NookieAI
-   stonemodder

See **THIRD_PARTY_NOTICES.md** for full licensing information.

------------------------------------------------------------------------

# ⚠ Disclaimer

This software is intended only for content you legally own.

It is **not affiliated with or endorsed by Sony Interactive
Entertainment**.

Use at your own risk.

------------------------------------------------------------------------

# ⭐ Support the Project

If you enjoy exFAT Image Builder:

-   ⭐ Star the repository
-   🐞 Report bugs
-   💡 Suggest features
-   ❤️ Support the PS5 Homebrew community

Made with ☕ and a passion for PS5 homebrew.


