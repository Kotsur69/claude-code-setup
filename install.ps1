# Installs this configuration into ~/.claude.
#
# Copies the tracked config files, rewriting the hardcoded user path inside
# settings.json so the hook commands resolve on this machine. Every file that
# would be overwritten is backed up to *.bak-<timestamp> first.
#
# Run with -DryRun to see what it would touch without writing anything.

[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Source = $PSScriptRoot
$Target = Join-Path $env:USERPROFILE '.claude'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

# The path baked into the hook commands in the committed settings.json.
$AuthoredHome = 'C:/Users/mmazur'
$ThisHome = ($env:USERPROFILE -replace '\\', '/')

Write-Host "Source: $Source"
Write-Host "Target: $Target"
if ($DryRun) { Write-Host 'DRY RUN - nothing will be written' -ForegroundColor Yellow }
Write-Host ''

if (-not (Test-Path $Target)) {
    Write-Host "Target does not exist. Install Claude Code and launch it once first." -ForegroundColor Red
    exit 1
}

# Relative paths to install, source -> same path under ~/.claude.
$Files = @(
    'CLAUDE.md',
    'settings.json',
    'settings.local.json',
    'hooks/cbm-session-reminder',
    'hooks/cbm-subagent-reminder',
    'rules/ecc/common/agents.md',
    'templates/repo-CLAUDE.md',
    'helpers/luna-statusline.cjs'
)

function Backup-IfPresent {
    param([string]$Path)
    if (Test-Path $Path) {
        $backup = "$Path.bak-$Stamp"
        Write-Host "  backup -> $(Split-Path $backup -Leaf)" -ForegroundColor DarkGray
        if (-not $DryRun) { Copy-Item $Path $backup -Force }
        return $true
    }
    return $false
}

foreach ($rel in $Files) {
    $src = Join-Path $Source ($rel -replace '/', '\')
    $dst = Join-Path $Target ($rel -replace '/', '\')

    if (-not (Test-Path $src)) {
        Write-Host "SKIP (missing in repo): $rel" -ForegroundColor Yellow
        continue
    }

    Write-Host "$rel"
    Backup-IfPresent -Path $dst | Out-Null

    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) {
        if (-not $DryRun) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    }

    if ($rel -eq 'settings.json') {
        # Rewrite the authored home path so the hook commands resolve here.
        $content = Get-Content $src -Raw
        if ($AuthoredHome -ne $ThisHome) {
            $content = $content.Replace($AuthoredHome, $ThisHome)
            Write-Host "  rewrote $AuthoredHome -> $ThisHome" -ForegroundColor Cyan
        }
        if (-not $DryRun) { Set-Content -Path $dst -Value $content -Encoding utf8 -NoNewline }
    }
    else {
        if (-not $DryRun) { Copy-Item $src $dst -Force }
    }
}

Write-Host ''
Write-Host 'Done.' -ForegroundColor Green
Write-Host ''
Write-Host 'Next:'
Write-Host '  1. Launch claude - the marketplaces and plugins in settings.json install themselves.'
Write-Host '  2. Verify with /plugin and /ecc:ecc-guide.'
Write-Host '  3. mcp.json.example is NOT installed. Copy it to ~/.claude/.mcp.json by hand'
Write-Host '     and set the referenced environment variables if you want those servers.'
Write-Host '  4. The statusline needs node on PATH. Drop the statusLine block from'
Write-Host '     settings.json if you do not want it.'
