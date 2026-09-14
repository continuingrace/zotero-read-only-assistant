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

& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name "Zotero-ChatGPT-MCP" `
    --distpath $releaseDir `
    --workpath (Join-Path $workDir "stdio") `
    --specpath $specDir `
    --collect-all pydantic `
    --hidden-import httpx `
    (Join-Path $projectRoot "stdio_entry.py")

$pluginDir = Join-Path $projectRoot "plugins\zotero-chatgpt"
$pluginBin = Join-Path $pluginDir "bin"
New-Item -ItemType Directory -Force -Path $pluginBin | Out-Null
Copy-Item -Force (Join-Path $releaseDir "Zotero-ChatGPT-MCP.exe") (Join-Path $pluginBin "Zotero-ChatGPT-MCP.exe")

& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "Install-Zotero-for-ChatGPT" `
    --distpath $releaseDir `
    --workpath (Join-Path $workDir "setup") `
    --specpath $specDir `
    --add-data "$pluginDir;payload\zotero-chatgpt" `
    (Join-Path $projectRoot "setup_entry.py")

Write-Host "Built: $releaseDir\Zotero-Read-Only-Assistant.exe"
Write-Host "Built: $releaseDir\Zotero-ChatGPT-MCP.exe"
Write-Host "Built: $releaseDir\Install-Zotero-for-ChatGPT.exe"
