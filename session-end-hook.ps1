# session-end-hook.ps1 -- appends a Claude Code session entry to today's Obsidian daily note
# Throttled: max once per 15 minutes to avoid spamming on every turn

$date  = Get-Date -Format "yyyy-MM-dd"
$time  = Get-Date -Format "HH:mm"
$vault = "$env:USERPROFILE\Documents\Ideaverse\Calendar\Daily"  # personal Obsidian vault -- likely N/A on a work PC, see SETUP.md
$note  = "$vault\$date.md"
$flag  = "$env:TEMP\claude-hook-$date.flag"

# Read hook data from stdin (Claude Code pipes JSON)
try {
    $raw  = [System.Console]::In.ReadToEnd()
    $data = $raw | ConvertFrom-Json -ErrorAction SilentlyContinue
} catch { $data = $null }

# Throttle -- skip if already written in the last 15 minutes
if (Test-Path $flag) {
    $age = (Get-Date) - (Get-Item $flag).LastWriteTime
    if ($age.TotalMinutes -lt 15) { exit 0 }
}
$null = New-Item $flag -ItemType File -Force

# Create daily note from template if it does not exist
if (-not (Test-Path $note)) {
    $null = New-Item -ItemType Directory -Force $vault
    $week = Get-Date -UFormat "%G-W%V"
    $template = "# $date`n`n## Done`n-`n`n## Top priority tomorrow`n-`n`n## Blockers`n-`n`n## Loose threads`n-`n`n---`n*Weekly review: [[$week]]*`n"
    Set-Content $note $template -Encoding utf8
}

# Build entry line
$cwd = if ($data.cwd) { $data.cwd -replace [regex]::Escape("$env:USERPROFILE\"), "~\" } else { "~\.local\bin" }
$entry = "- $time -- Claude Code @ $cwd"

# Append under Claude Sessions section (create section if missing)
$content = Get-Content $note -Raw -ErrorAction SilentlyContinue
if ($content -notmatch "## Claude Sessions") {
    Add-Content $note "`n## Claude Sessions"
}
Add-Content $note $entry
