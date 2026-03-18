param(
    [string]$PythonExe = ".venv\Scripts\python.exe",
    [string]$Version = "1.0.0",
    [switch]$CreateInstaller
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Write-Host "[1/5] Installing app dependencies..."
& $PythonExe -m pip install -r requirements.txt

Write-Host "[2/5] Installing build dependencies..."
& $PythonExe -m pip install -r requirements-build.txt

Write-Host "[3/5] Cleaning previous build outputs..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "[4/5] Building MasterForge 320 executable..."
& $PythonExe -m PyInstaller --noconfirm masterforge.spec

Write-Host "[5/5] Creating distributable zip..."
$zipPath = "dist\MasterForge320-windows-x64.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path "dist\MasterForge320\*" -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Build complete: $zipPath"

if ($CreateInstaller) {
    Write-Host "[Installer] Looking for Inno Setup compiler (ISCC.exe)..."

    $isccCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        (Get-Command iscc.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
    ) | Where-Object { $_ -and (Test-Path $_) }

    $iscc = $isccCandidates | Select-Object -First 1
    if (-not $iscc) {
        throw "Inno Setup compiler not found. Install Inno Setup 6, then run again with -CreateInstaller."
    }

    $issPath = Join-Path $root "installer\MasterForge320.iss"
    if (-not (Test-Path $issPath)) {
        throw "Installer script not found: $issPath"
    }

    Write-Host "[Installer] Building setup executable..."
    & $iscc "/DMyAppVersion=$Version" "/DMyAppSourceDir=$root\dist\MasterForge320" "/DMyOutputDir=$root\dist" $issPath

    Write-Host "Installer complete in dist\ (MasterForge320-Setup-$Version-x64.exe)"
}
