$ErrorActionPreference = 'Stop'

$backend = Resolve-Path "$PSScriptRoot\..\backend"
$python = Join-Path $backend '.venv\Scripts\python.exe'
if (!(Test-Path $python)) {
  throw 'Backend virtual environment missing. Run scripts/setup_windows.ps1 first.'
}
if (!(Test-Path (Join-Path $backend '.env'))) {
  Write-Warning 'backend/.env is missing; development defaults will be used. Run scripts/setup_windows.ps1 to generate a local secret.'
}

Push-Location $backend
try {
  Write-Host 'API health: http://127.0.0.1:8000/api/v1/health'
  Write-Host 'API docs:   http://127.0.0.1:8000/docs'
  & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} finally {
  Pop-Location
}
