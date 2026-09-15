$ErrorActionPreference = "Stop"

function Show-InstallerMessage {
    param([string]$Text, [string]$Title, [string]$Icon)
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($Text, $Title, "OK", $Icon) | Out-Null
}

try {
    $source = Join-Path $PSScriptRoot "zotero-chatgpt"
    $manifest = Join-Path $source ".codex-plugin\plugin.json"
    if (-not (Test-Path -LiteralPath $manifest)) {
        throw "압축을 먼저 완전히 풀어 주세요. zotero-chatgpt 폴더를 찾을 수 없습니다."
    }

    $profileRoot = if ($env:ZOTERO_CHATGPT_TEST_PROFILE) { $env:ZOTERO_CHATGPT_TEST_PROFILE } else { $env:USERPROFILE }
    if (-not $profileRoot) { throw "Windows 사용자 폴더를 확인할 수 없습니다." }

    $targetParent = Join-Path $profileRoot "plugins"
    $target = Join-Path $targetParent "zotero-chatgpt"
    New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
    Copy-Item -LiteralPath $source -Destination $targetParent -Recurse -Force

    $marketplaceRoot = Join-Path $profileRoot ".agents\plugins"
    $marketplacePath = Join-Path $marketplaceRoot "marketplace.json"
    New-Item -ItemType Directory -Force -Path $marketplaceRoot | Out-Null

    if (Test-Path -LiteralPath $marketplacePath) {
        $marketplace = Get-Content -LiteralPath $marketplacePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } else {
        $marketplace = [pscustomobject]@{
            name = "personal"
            interface = [pscustomobject]@{ displayName = "Personal" }
            plugins = @()
        }
    }

    $kept = @($marketplace.plugins | Where-Object { $_.name -ne "zotero-chatgpt" })
    $entry = [pscustomobject]@{
        name = "zotero-chatgpt"
        source = [pscustomobject]@{ source = "local"; path = "./plugins/zotero-chatgpt" }
        policy = [pscustomobject]@{ installation = "AVAILABLE"; authentication = "ON_INSTALL" }
        category = "Education & Research"
    }
    $marketplace.plugins = @($kept) + @($entry)
    $marketplace | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $marketplacePath -Encoding UTF8

    if ($env:ZOTERO_CHATGPT_TEST_PROFILE) {
        Write-Output "INSTALL TEST OK"
    } else {
        Show-InstallerMessage -Title "Zotero for ChatGPT 설치" -Icon "Information" -Text "설치가 완료되었습니다.`n`n1. Zotero Desktop을 열어 두세요.`n2. ChatGPT 데스크톱 앱을 완전히 종료한 뒤 다시 여세요.`n3. 플러그인 > Personal에서 Zotero for ChatGPT를 설치하세요.`n4. 새 일반 Chat에서 최근 Zotero 자료 3개를 찾아 달라고 해보세요."
    }
} catch {
    if ($env:ZOTERO_CHATGPT_TEST_PROFILE) {
        Write-Error $_
    } else {
        Show-InstallerMessage -Title "Zotero for ChatGPT 설치 오류" -Icon "Error" -Text "설치하지 못했습니다.`n`n$($_.Exception.Message)"
    }
    exit 1
}
