$ErrorActionPreference = 'Stop'

$frontend = Resolve-Path "$PSScriptRoot\..\frontend"
if (!(Test-Path (Join-Path $frontend 'node_modules'))) {
  throw 'Frontend dependencies missing. Run scripts/setup_windows.ps1 first.'
}

Push-Location $frontend
try {
  Write-Host 'Console: http://127.0.0.1:5173'
  npm run dev
} finally {
  Pop-Location
}
