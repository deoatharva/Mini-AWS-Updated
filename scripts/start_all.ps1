$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot\.."
$backendScript = Join-Path $PSScriptRoot 'start_backend.ps1'
$frontendScript = Join-Path $PSScriptRoot 'start_frontend.ps1'

Start-Process -FilePath 'powershell.exe' `
  -WorkingDirectory $root `
  -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$backendScript`""
Start-Process -FilePath 'powershell.exe' `
  -WorkingDirectory $root `
  -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$frontendScript`""

Write-Host 'Launched backend and frontend in separate PowerShell windows.'
Write-Host 'Backend health: http://127.0.0.1:8000/api/v1/health'
Write-Host 'Frontend:       http://127.0.0.1:5173'
