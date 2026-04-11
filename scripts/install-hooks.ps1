# Install git hooks from scripts/templates into .git/hooks (Windows / PowerShell).
# Usage:  pwsh -File scripts/install-hooks.ps1
#    or:  powershell -ExecutionPolicy Bypass -File scripts/install-hooks.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$HooksDir = Join-Path $RepoRoot ".git/hooks"
$TemplatesDir = Join-Path $RepoRoot "scripts/templates"

if (-not (Test-Path $HooksDir)) {
    Write-Host "No .git/hooks found. Initialize git in this repo first, then re-run." -ForegroundColor Yellow
    exit 1
}

$hookNames = @("pre-commit", "pre-push", "commit-msg", "pre-merge-commit")

Write-Host "Installing git hooks into $HooksDir ..." -ForegroundColor Cyan

foreach ($name in $hookNames) {
    $src = Join-Path $TemplatesDir $name
    $dest = Join-Path $HooksDir $name
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dest -Force
        Write-Host "  OK  $name" -ForegroundColor Green
    }
    else {
        Write-Host "  SKIP  $name (template missing)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Done. Hooks match scripts/templates (same as install-hooks.sh)." -ForegroundColor Cyan
Write-Host "Optional JSON config: copy .hooks-config.example.json (see README.md)" -ForegroundColor DarkGray
