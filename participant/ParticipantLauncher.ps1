$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$participantDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $participantDir
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pidFile = Join-Path $participantDir ".bridge.pid"
$logFile = Join-Path $participantDir "bridge.log"
$errorLogFile = Join-Path $participantDir "bridge-error.log"
$configFile = Join-Path $participantDir "participant-config.json"

trap {
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "Zotero Read-only Bridge", "OK", "Error") | Out-Null
    exit 1
}

function Show-Message([string]$message, [string]$title = "Zotero Read-only Bridge") {
    [System.Windows.Forms.MessageBox]::Show($message, $title, "OK", "Information") | Out-Null
}

function Show-Error([string]$message) {
    [System.Windows.Forms.MessageBox]::Show($message, "Setup required", "OK", "Error") | Out-Null
}

function Invoke-Hidden([string]$filePath, [string[]]$arguments, [string]$workingDirectory) {
    $process = Start-Process -FilePath $filePath -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Setup failed. Please check bridge-error.log."
    }
}

function Ensure-Setup {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $systemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $systemPython) {
            throw "Python 3.11 or newer is required. Please contact the administrator."
        }
        Invoke-Hidden $systemPython @("-m", "venv", ".venv") $projectRoot
        Invoke-Hidden $venvPython @("-m", "pip", "install", "-r", (Join-Path $participantDir "requirements.txt")) $projectRoot
    }

    $envFile = Join-Path $projectRoot ".env"
    if (-not (Test-Path -LiteralPath $envFile)) {
        $token = (& $venvPython -c "import secrets; print(secrets.token_urlsafe(32))").Trim()
        $template = Get-Content (Join-Path $projectRoot ".env.example") -Raw
        $template.Replace("replace-with-a-random-token-of-at-least-32-characters", $token) | Set-Content -Path $envFile -Encoding UTF8
    }
}

function Get-BridgeProcess {
    $pidFile = Join-Path $participantDir ".bridge.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { return $null }
    $savedPid = Get-Content $pidFile -Raw
    $process = Get-Process -Id ([int]$savedPid.Trim()) -ErrorAction SilentlyContinue
    if (-not $process) { Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue }
    return $process
}

function Start-Bridge {
    Ensure-Setup
    if (Get-BridgeProcess) { return }
    $process = Start-Process -FilePath $venvPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8787") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile
    $process.Id | Set-Content -Path $pidFile -Encoding ASCII
    Start-Sleep -Milliseconds 800
    Start-Process "http://127.0.0.1:8787/reader"
}

function Stop-Bridge {
    $process = Get-BridgeProcess
    if ($process) { Stop-Process -Id $process.Id -Force }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

function Get-McpUrl {
    if (-not (Test-Path -LiteralPath $configFile)) { return $null }
    try {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        return [string]$config.mcp_url
    } catch {
        return $null
    }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Zotero Read-only Bridge"
$form.Size = New-Object System.Drawing.Size(480, 300)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "Zotero Read-only Bridge"
$title.Font = New-Object System.Drawing.Font("맑은 고딕", 16, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(25, 20)
$title.AutoSize = $true
$form.Controls.Add($title)

$status = New-Object System.Windows.Forms.Label
$status.Text = "Checking status..."
$status.Location = New-Object System.Drawing.Point(28, 65)
$status.AutoSize = $true
$form.Controls.Add($status)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = "Open Zotero first, then click Setup and Start."
$hint.Location = New-Object System.Drawing.Point(28, 95)
$hint.AutoSize = $true
$form.Controls.Add($hint)

$start = New-Object System.Windows.Forms.Button
$start.Text = "Setup and Start"
$start.Location = New-Object System.Drawing.Point(28, 140)
$start.Size = New-Object System.Drawing.Size(125, 38)
$form.Controls.Add($start)

$stop = New-Object System.Windows.Forms.Button
$stop.Text = "Stop"
$stop.Location = New-Object System.Drawing.Point(165, 140)
$stop.Size = New-Object System.Drawing.Size(90, 38)
$form.Controls.Add($stop)

$copy = New-Object System.Windows.Forms.Button
$copy.Text = "Copy MCP URL (optional)"
$copy.Location = New-Object System.Drawing.Point(28, 195)
$copy.Size = New-Object System.Drawing.Size(125, 38)
$form.Controls.Add($copy)

$guide = New-Object System.Windows.Forms.Button
$guide.Text = "User Guide"
$guide.Location = New-Object System.Drawing.Point(165, 195)
$guide.Size = New-Object System.Drawing.Size(90, 38)
$form.Controls.Add($guide)

function Refresh-Status {
    if (Get-BridgeProcess) {
        $status.Text = "Running - read-only bridge is ready"
        $status.ForeColor = [System.Drawing.Color]::DarkGreen
    } else {
        $status.Text = "Stopped"
        $status.ForeColor = [System.Drawing.Color]::DarkRed
    }
}

$start.Add_Click({
    try { Start-Bridge; Refresh-Status } catch { Show-Error $_.Exception.Message }
})

$stop.Add_Click({
    try { Stop-Bridge; Refresh-Status } catch { Show-Error $_.Exception.Message }
})

$copy.Add_Click({
    $url = Get-McpUrl
    if (-not $url) {
        Show-Message "The administrator has not provided an MCP URL in participant-config.json." "MCP URL missing"
    } else {
        [System.Windows.Forms.Clipboard]::SetText($url)
        Show-Message "The MCP URL was copied to the clipboard." "Copied"
    }
})

$guide.Add_Click({
    Start-Process (Join-Path $projectRoot "docs\participant-installation.md")
})

$form.Add_Shown({ Refresh-Status })
$form.Add_FormClosing({ Stop-Bridge })
[void]$form.ShowDialog()
