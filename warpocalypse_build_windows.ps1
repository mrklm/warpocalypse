# build_windows.ps1
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 1.1.6
#   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 1.1.6 --clean

param(
  [Parameter(Mandatory=$true, Position=0)]
  [string]$Version,

  [Parameter(Mandatory=$false)]
  [switch]$Clean
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------
# Build Windows Warpocalypse (onedir + zip + sha256)
# Sortie dans .\releases\
#   - warpocalypse-vX.X.X-windows-x86_64.zip + .sha256
#
# Embarque ffmpeg + ffprobe depuis:
#   - tools\windows-x86_64\ffmpeg.exe / ffprobe.exe (préféré)
#   - OU fallback: windows-x86_64\tools\ffmpeg.exe / ffprobe.exe
# ----------------------------------------------------

$AppName      = "warpocalypse"
$ProjectRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleasesDir  = Join-Path $ProjectRoot "releases"
$DistDir      = Join-Path $ProjectRoot "dist"
$BuildDir     = Join-Path $ProjectRoot "build"
$VenvDir      = Join-Path $ProjectRoot ".venv-build"
$SpecFile     = Join-Path $ProjectRoot "$AppName.spec"

$AssetsSrc    = Join-Path $ProjectRoot "assets"
$AssetsDst    = Join-Path (Join-Path $DistDir $AppName) "assets"

# Tools (chemin attendu)
$ToolsExpected = Join-Path (Join-Path $ProjectRoot "tools") "windows-x86_64"
$FfmpegExpected = Join-Path $ToolsExpected "ffmpeg.exe"
$FfprobeExpected = Join-Path $ToolsExpected "ffprobe.exe"

# Fallback (ton emplacement mentionné)
$ToolsFallback = Join-Path (Join-Path $ProjectRoot "windows-x86_64") "tools"
$FfmpegFallback = Join-Path $ToolsFallback "ffmpeg.exe"
$FfprobeFallback = Join-Path $ToolsFallback "ffprobe.exe"

function Die($msg) { throw $msg }

function Ensure-File($p, $label) {
  if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { Die "$label introuvable: $p" }
}

function Ensure-Dir($p, $label) {
  if (-not (Test-Path -LiteralPath $p -PathType Container)) { Die "$label introuvable: $p" }
}

function Get-ToolsSource {
  if ((Test-Path -LiteralPath $FfmpegExpected -PathType Leaf) -and (Test-Path -LiteralPath $FfprobeExpected -PathType Leaf)) {
    return $ToolsExpected
  }
  if ((Test-Path -LiteralPath $FfmpegFallback -PathType Leaf) -and (Test-Path -LiteralPath $FfprobeFallback -PathType Leaf)) {
    return $ToolsFallback
  }
  Die "ffmpeg/ffprobe introuvables. Attendu: `n- $FfmpegExpected + $FfprobeExpected`nOU fallback: `n- $FfmpegFallback + $FfprobeFallback"
}

# -------- sanity checks --------
Ensure-File (Join-Path $ProjectRoot "warpocalypse.py") "warpocalypse.py"
Ensure-File (Join-Path $ProjectRoot "requirements.txt") "requirements.txt"
Ensure-Dir  $AssetsSrc "assets/"

$ToolsSrc = Get-ToolsSource
$FfmpegSrc = Join-Path $ToolsSrc "ffmpeg.exe"
$FfprobeSrc = Join-Path $ToolsSrc "ffprobe.exe"
Ensure-File $FfmpegSrc "ffmpeg.exe"
Ensure-File $FfprobeSrc "ffprobe.exe"

# -------- clean begin --------
if (Test-Path -LiteralPath $BuildDir) { Remove-Item -Recurse -Force -LiteralPath $BuildDir }
if (Test-Path -LiteralPath $DistDir)  { Remove-Item -Recurse -Force -LiteralPath $DistDir }
if (Test-Path -LiteralPath $SpecFile) { Remove-Item -Force -LiteralPath $SpecFile }

New-Item -ItemType Directory -Force -Path $ReleasesDir | Out-Null

# -------- venv build --------
python -m venv $VenvDir
$Py = Join-Path (Join-Path $VenvDir "Scripts") "python.exe"
& $Py -m pip install -U pip wheel setuptools | Out-Null
& $Py -m pip install -r (Join-Path $ProjectRoot "requirements.txt") | Out-Null
& $Py -m pip install pyinstaller | Out-Null

# -------- pyinstaller (onedir + windowed) --------
& $Py -m PyInstaller `
  --noconfirm `
  --clean `
  --name $AppName `
  --onedir `
  --windowed `
  (Join-Path $ProjectRoot "warpocalypse.py")

$ExePath = Join-Path (Join-Path (Join-Path $DistDir $AppName) "") "$AppName.exe"
Ensure-File $ExePath "Binaire PyInstaller"

# Supprime le .spec généré
if (Test-Path -LiteralPath $SpecFile) { Remove-Item -Force -LiteralPath $SpecFile }

# -------- inject assets into dist --------
# => dist\warpocalypse\assets\...
if (Test-Path -LiteralPath $AssetsDst) { Remove-Item -Recurse -Force -LiteralPath $AssetsDst }
Copy-Item -Recurse -Force -LiteralPath $AssetsSrc -Destination $AssetsDst

Ensure-File (Join-Path $AssetsDst "AIDE.md") "assets/AIDE.md dans dist"

# -------- inject tools into dist --------
# => dist\warpocalypse\tools\windows-x86_64\ffmpeg.exe
$ToolsDst = Join-Path (Join-Path (Join-Path $DistDir $AppName) "tools") "windows-x86_64"
New-Item -ItemType Directory -Force -Path $ToolsDst | Out-Null
Copy-Item -Force -LiteralPath $FfmpegSrc  -Destination (Join-Path $ToolsDst "ffmpeg.exe")
Copy-Item -Force -LiteralPath $FfprobeSrc -Destination (Join-Path $ToolsDst "ffprobe.exe")

# -------- zip release --------
$ZipName = "$AppName-v$Version-windows-x86_64.zip"
$ZipOut  = Join-Path $ReleasesDir $ZipName

if (Test-Path -LiteralPath $ZipOut) { Remove-Item -Force -LiteralPath $ZipOut }

# On zip le dossier dist\warpocalypse\ (le contenu sera dans un dossier warpocalypse/ dans le zip)
Compress-Archive -Path (Join-Path $DistDir $AppName) -DestinationPath $ZipOut

# -------- sha256 --------
$Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ZipOut).Hash.ToLower()
Set-Content -LiteralPath ($ZipOut + ".sha256") -Value "$Hash  $ZipName" -Encoding ASCII

Write-Host ""
Write-Host "Build terminé."
Write-Host "Sorties:"
Get-ChildItem -LiteralPath $ReleasesDir | Sort-Object Name | Format-Table Name, Length

# -------- clean end (optional) --------
# Supprime le .spec même si Clean n'est pas demandé
if (Test-Path -LiteralPath $SpecFile) { Remove-Item -Force -LiteralPath $SpecFile }

if ($Clean) {
  if (Test-Path -LiteralPath $BuildDir) { Remove-Item -Recurse -Force -LiteralPath $BuildDir }
  if (Test-Path -LiteralPath $DistDir)  { Remove-Item -Recurse -Force -LiteralPath $DistDir }
  if (Test-Path -LiteralPath $VenvDir)  { Remove-Item -Recurse -Force -LiteralPath $VenvDir }
  Write-Host "Nettoyage effectué (build/dist/.venv-build supprimés)."
} else {
  Write-Host "Nettoyage non effectué. Ajouter --clean pour supprimer build/dist/.venv-build."
}
