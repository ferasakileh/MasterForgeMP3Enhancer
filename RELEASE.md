# MasterForge 320 – Production Build & Distribution

This project can be packaged as a Windows desktop app (`MasterForge320.exe`) and distributed as either:

- a portable ZIP
- a standard installer (`Next/Install`) built with Inno Setup

## 1) Local production build (Windows)

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1
```

Build output:

- `dist/MasterForge320/` (portable app folder)
- `dist/MasterForge320-windows-x64.zip` (downloadable package)

## 1.1) Build installer (recommended for end users)

Install Inno Setup 6:

```powershell
winget install JRSoftware.InnoSetup
```

Then run:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1 -CreateInstaller -Version 1.0.0
```

Installer output:

- `dist/MasterForge320-Setup-1.0.0-x64.exe`

Installer script:

- `installer/MasterForge320.iss`

Run app directly:

```powershell
.\dist\MasterForge320\MasterForge320.exe
```

## 2) Share with users

Upload one (or both):

- `dist/MasterForge320-Setup-<version>-x64.exe` (recommended)
- `dist/MasterForge320-windows-x64.zip`

to:

- GitHub Releases
- Website download page
- Cloud storage (S3, Azure Blob, etc.)

## 3) Important runtime requirement

MP3 export requires FFmpeg available on user machines.

Recommended:

- Install FFmpeg and ensure `ffmpeg` is in `PATH`, or
- Set `FFMPEG_BINARY` environment variable to full `ffmpeg.exe` path.

## 4) Optional hardening for true production

- Code sign `MasterForge320.exe` (prevents SmartScreen warnings)
- Code sign `MasterForge320-Setup-<version>-x64.exe`
- Optional future upgrade: MSIX packaging
- Add crash telemetry and logs
- Pin dependency versions in `requirements.txt`
