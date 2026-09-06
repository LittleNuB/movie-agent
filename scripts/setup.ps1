param([switch]$SkipMediaTools)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoRoot
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ then run this script again.'
    }
    uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency setup failed.' }
    $mediaDir = Join-Path $repoRoot '.cache\tools\ffmpeg'
    $ffmpeg = Get-ChildItem -LiteralPath $mediaDir -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $SkipMediaTools -and -not $ffmpeg -and -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        New-Item -ItemType Directory -Path $mediaDir -Force | Out-Null
        $archive = Join-Path $mediaDir 'ffmpeg-release-essentials.zip'
        $url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        Write-Host 'Downloading FFmpeg essentials and checking its published SHA256...'
        $receipt = (Invoke-WebRequest -UseBasicParsing -Uri "$url.sha256").Content
        if ($receipt -is [byte[]]) { $receipt = [Text.Encoding]::UTF8.GetString($receipt) }
        $expectedHash = [regex]::Match([string]$receipt, '[a-fA-F0-9]{64}').Value.ToUpperInvariant()
        if (-not $expectedHash) { throw 'No valid FFmpeg checksum received.' }
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) {
            throw 'FFmpeg checksum mismatch. Archive was not extracted.'
        }
        Expand-Archive -LiteralPath $archive -DestinationPath $mediaDir -Force
        Write-Host "FFmpeg SHA256: $expectedHash"
    }
    Write-Host 'Setup complete. Start with: .\scripts\start.ps1'
} finally { Pop-Location }
