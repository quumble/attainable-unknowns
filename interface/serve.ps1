$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
Write-Host "Serving Attainable Unknowns at http://localhost:8000/interface/"
python -m http.server 8000
