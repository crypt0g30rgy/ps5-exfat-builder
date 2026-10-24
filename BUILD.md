# Building exFAT Image Builder from Source

This guide covers a local Windows build and the automated GitHub Actions
build/release pipeline. The application is **Windows-only** (Windows 10/11,
x64) and is packaged as a single `--onefile` PyInstaller executable.

The canonical local build is `build.bat`. The CI workflow mirrors it so a
release produced by GitHub Actions and a local build use the same
PyInstaller options.

---

## Requirements

| Requirement | Notes |
| --- | --- |
| Windows 10 or 11 (x64) | The app uses Win32 APIs, OSFMount and PowerShell. Linux/macOS cannot build the Windows exe. |
| Python 3.11 (x64) | From <https://www.python.org/downloads/windows/>. Tick **Add python.exe to PATH** and leave **tcl/tk and IDLE** enabled. |
| Git for Windows | Or download the source archive and extract it. |
| Internet access | Needed to install Python packages. |
| ~2 GB free disk space | PyInstaller work directory, virtualenv and output. |

You do **not** need Visual Studio, a C compiler, or administrator rights to
build. OSFMount and .NET 8 are runtime requirements for some features, not
build requirements.

Check your interpreter:

```powershell
py -0p
python --version
python -c "import tkinter; print('tkinter OK')"
```

`python --version` must report 3.11.x, and the tkinter check must succeed.
If tkinter fails, reinstall Python with the tcl/tk option enabled.

---

## 1. Get the source

```powershell
git clone https://github.com/kerrdec97/ps5-exfat-builder.git
cd ps5-exfat-builder
```

Run every command below from the repository root (the folder containing
`exfat_builder.py`, `build.bat`, `controller.ico`, `ui\` and `assets\`).

---

## 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation, allow it for the current shell only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternatively, use Command Prompt: `.\.venv\Scripts\activate.bat`.

---

## 3. Install dependencies

```powershell
python -m pip install pyinstaller pillow tkinterdnd2 psutil "mkpfs==0.0.8" cryptography
```

Why these packages:

- **pyinstaller** — produces the single-file executable.
- **pillow** — cover art and image thumbnails.
- **tkinterdnd2** — drag-and-drop file/folder support.
- **psutil** — process and system resource information.
- **mkpfs==0.0.8** — the PFS packer. Keep this pin: it matches
  `build.bat` and the tested release configuration.
- **cryptography** — required by the mkpfs stack.

`tkinterweb` is **optional**. If installed, the Help tab uses a rich HTML
viewer; without it the app uses its built-in text fallback. It is not part
of the release build.

---

## 4. Run the tests

```powershell
python -m unittest discover -s tests -v
```

The suite is pure Python (no Tk window is created) and covers naming,
embedded payloads, process supervision, hardware detection, responsive
scaling, robocopy summary parsing, queue size overrides, and windowed
stdio hardening.

---

## 5. Smoke-test from source

```powershell
python exfat_builder.py
```

Windows is required for the full UI and for OSFMount / PowerShell / WMI
integration. Confirm the window opens, the version in the About tab is
correct, and the main tabs render.

---

## 6. Build the executable

### Option A — recommended: `build.bat`

```powershell
.\build.bat
```

The script installs the build dependencies with `py -3.11` (including the
pinned `mkpfs==0.0.8`), embeds `controller.ico`, and builds the full
application. If `exfat_builder_lite.py` exists it also builds the Lite
variant; this repository ships only the full build.

Output: `dist\exFAT Image Builder.exe`

### Option B — explicit PyInstaller command

Use this when you want to see or modify each flag. It is the same command
the GitHub Actions workflow runs:

```powershell
python -m PyInstaller --onefile --windowed --clean --noconfirm `
  --name "exFAT Image Builder" `
  --icon "controller.ico" `
  --hidden-import PIL._tkinter_finder `
  --hidden-import psutil `
  --hidden-import mkpfs `
  --hidden-import mkpfs.__main__ `
  --hidden-import mkpfs.cli `
  --hidden-import mkpfs.pfs `
  --hidden-import mkpfs.utils `
  --hidden-import mkpfs.consts `
  --hidden-import mkpfs.logging `
  --hidden-import mkpfs.pbar `
  --hidden-import cryptography `
  --hidden-import cryptography.hazmat.primitives.ciphers `
  --hidden-import cryptography.hazmat.primitives.ciphers.algorithms `
  --hidden-import cryptography.hazmat.primitives.ciphers.modes `
  --hidden-import cryptography.hazmat.backends `
  --hidden-import cryptography.hazmat.backends.openssl `
  --hidden-import cryptography.hazmat.backends.openssl.backend `
  --collect-all mkpfs `
  --collect-all cryptography `
  --collect-all tkinterdnd2 `
  --collect-submodules ui `
  --collect-submodules ui.shared `
  --paths . `
  exfat_builder.py
```

Important build notes:

- `--onefile` produces one exe that unpacks to a temporary `_MEI...`
  folder at launch. First start is slower than subsequent starts; this is
  normal.
- `--windowed` suppresses the console window. The app re-launches itself
  in `--__mkpfs_worker__` mode for packaging, so do not remove that
  handling.
- `--collect-all` is required for mkpfs, cryptography and tkinterdnd2
  data/binaries.
- If `controller.ico` is missing, remove the `--icon` argument.
- Close any running copy of the app before rebuilding; Windows will not
  overwrite a running exe.

### Clean build

PyInstaller caches analysis in `build\`. For a clean rebuild:

```powershell
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
.\build.bat
```

---

## 7. Generate the SHA256 checksum

The in-app updater verifies a `.sha256` asset when one is present. Create
it next to the exe:

```powershell
$h = (Get-FileHash -Algorithm SHA256 'dist\exFAT Image Builder.exe').Hash.ToLower()
"$h  exFAT Image Builder.exe" | Out-File -Encoding ASCII 'dist\exFAT Image Builder.exe.sha256'
Get-Content 'dist\exFAT Image Builder.exe.sha256'
```

Keep this exact naming convention:

- `exFAT Image Builder.exe`
- `exFAT Image Builder.exe.sha256`

The updater selects a release asset ending in `.exe` that does not contain
`Lite`, plus a `.sha256` asset that does not contain `Lite`. A renamed
asset will not be picked up.

---

## 8. Verify the build

- Launch `dist\exFAT Image Builder.exe` and check the version shown in the
  title bar / About tab.
- Confirm the exe is a realistic size. The app rejects updater downloads
  under 5 MB, so a release exe should be comfortably larger.
- Compare the file hash with the generated checksum:

```powershell
Get-FileHash -Algorithm SHA256 'dist\exFAT Image Builder.exe'
```

- For a true release check, copy the exe to a clean Windows VM without
  Python installed and launch it there. This catches missing
  `--collect-all` / hidden-import dependencies.

---

## GitHub Actions

Workflow: `.github/workflows/build-release.yml`.

### Triggers

| Event | What happens |
| --- | --- |
| Pull request | Installs dependencies, runs tests, builds the exe, uploads an artifact. No release. |
| Push to `main` | Same build and artifact upload. No release. |
| Push a tag matching `v*` | Builds, verifies the tag matches `APP_VERSION`, then publishes a GitHub Release with the exe and checksum. |
| Manual `workflow_dispatch` | Builds and uploads the artifact only. |

The build job runs on `windows-latest` with Python 3.11 x64. Artifacts are
named `exfat-image-builder-windows-x64` and kept for 30 days.

### Publishing a release

1. Update the version in `exfat_builder.py`:

   ```python
   APP_VERSION = '3.6.5'
   ```

2. Optionally update the changelog and commit both changes.

3. Create and push an annotated tag:

   ```powershell
   git tag -a v3.6.5 -m "exFAT Image Builder v3.6.5"
   git push origin v3.6.5
   ```

4. The workflow runs automatically. The tag **must** match
   `APP_VERSION` prefixed with `v`; otherwise the build fails before
   packaging and no release is created.

5. On success, the release contains:

   - `exFAT Image Builder.exe`
   - `exFAT Image Builder.exe.sha256`

   Release notes are generated from the commit history. If a release for
   that tag already exists, the workflow re-uploads both assets with
   `--clobber` instead of failing.

No repository secrets are required: the workflow uses the built-in
`GITHUB_TOKEN` and requests `contents: write` only in the release job.

If release creation fails with HTTP 403, check **Settings → Actions →
General → Workflow permissions** and allow read and write permissions for
the repository token.

### Build from a manual workflow run

1. Open **Actions → Build and Release → Run workflow**.
2. Select the branch and run it.
3. When it finishes, download `exfat-image-builder-windows-x64` from the
   run's **Artifacts** section.

Manual runs do not create a release.

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'tkinter'`** — Reinstall
  Python 3.11 with the tcl/tk / IDLE component selected.
- **`ModuleNotFoundError: No module named 'mkpfs'`** — Activate the
  virtual environment and install the pinned package:
  `python -m pip install "mkpfs==0.0.8"`.
- **PyInstaller cannot find tkinterdnd2 data** — Keep
  `--collect-all tkinterdnd2` in the command.
- **The exe opens and closes immediately** — Build without `--windowed`
  temporarily (or run from a terminal) to see the traceback. Common
  causes are a missing hidden import or running a release built for a
  different architecture.
- **Antivirus or SmartScreen flags the exe** — Unsigned `--onefile`
  PyInstaller executables are frequently flagged as false positives.
  Verify the SHA256, build from a clean checkout, and consider code
  signing for public distribution.
- **The app cannot replace itself during an update** — The running exe
  is locked. Exit the app completely and retry; the updater may need a
  moment for the onefile `_MEI` cleanup.
- **A release is created but the in-app updater does not see it** —
  Confirm the assets keep the exact names above, that the release is the
  repository's latest, and that assets are attached to the release (not
  just the workflow run). The updater reads `releases/latest` from
  `kerrdec97/ps5-exfat-builder`.
