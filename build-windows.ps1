$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildPython = Join-Path $projectRoot ".build-venv\Scripts\python.exe"
$releaseDir = Join-Path $projectRoot "release"
$workDir = Join-Path $projectRoot ".build\pyinstaller"
$specDir = Join-Path $projectRoot ".build\spec"

if (-not (Test-Path -LiteralPath $buildPython)) {
    python -m venv (Join-Path $projectRoot ".build-venv")
}

& $buildPython -m pip install --disable-pip-version-check --no-input -r (Join-Path $projectRoot "participant\requirements.txt") -r (Join-Path $projectRoot "requirements-build.txt")

& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "Zotero-Read-Only-Assistant" `
    --distpath $releaseDir `
    --workpath $workDir `
    --specpath $specDir `
    --collect-all fastapi `
    --collect-all pydantic `
    --collect-all starlette `
    --hidden-import uvicorn.logging `
    --hidden-import uvicorn.loops.auto `
    --hidden-import uvicorn.protocols.http.auto `
    --hidden-import uvicorn.protocols.websockets.auto `
    --hidden-import uvicorn.lifespan.on `
    (Join-Path $projectRoot "desktop_entry.py")

Write-Host "Built: $releaseDir\Zotero-Read-Only-Assistant.exe"
