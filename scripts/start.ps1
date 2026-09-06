param([int]$Port = 4318)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoRoot
try {
    $env:MOVIE_AGENT_PORT = [string]$Port
    uv run --frozen python -m movie_agent
} finally { Pop-Location }
