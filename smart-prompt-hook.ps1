# smart-prompt-hook.ps1 -- runs before every user message
# Routes the task via ruflo and injects tool suggestions into Claude's context

$raw = ""
try { $raw = [System.Console]::In.ReadToEnd() } catch { exit 0 }
$data = $raw | ConvertFrom-Json -ErrorAction SilentlyContinue
$prompt = if ($data.prompt) { $data.prompt } else { exit 0 }

# Skip very short prompts (single words, yes/no etc.)
if ($prompt.Length -lt 12) { exit 0 }

$ruflo = "ruflo"  # relies on global npm bin being on PATH

# 1. Route: which agent/tools are best for this task
$routeOut = & $ruflo hooks route --task $prompt 2>&1
$routeText = ($routeOut | Where-Object { $_ -match "Agent|Tool|Pattern|Route|Suggest" }) -join " | "
if (-not $routeText) { $routeText = ($routeOut | Select-Object -First 3) -join " " }

# 2. Quick memory search for relevant patterns (max 2 results)
$memOut = & $ruflo memory search --query $prompt --limit 2 --namespace patterns 2>&1
$memText = ($memOut | Where-Object { $_ -match "\S" } | Select-Object -First 3) -join " "

# 3. Detect project context from cwd or prompt
$cwd = if ($data.cwd) { $data.cwd } else { "" }
$projectHint = ""
if ($cwd -match "synthara" -or $prompt -match "synthara") { $projectHint = "PROJECT:synthara graphify-out available" }
elseif ($cwd -match "luna-voice" -or $prompt -match "luna.voice|luna voice") { $projectHint = "PROJECT:luna-voice graphify-out available" }
elseif ($cwd -match "crypto" -or $prompt -match "crypto|trading.bot") { $projectHint = "PROJECT:crypto graphify-out available" }

# Output context injection (appears in [INTELLIGENCE] system-reminder)
$parts = @()
if ($routeText -and $routeText.Length -gt 5) { $parts += "ROUTE: $routeText" }
if ($memText -and $memText.Length -gt 5)     { $parts += "MEMORY: $memText" }
if ($projectHint)                             { $parts += $projectHint }

if ($parts.Count -gt 0) {
    Write-Output "[INTELLIGENCE] $($parts -join ' || ')"
}
