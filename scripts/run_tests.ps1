$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot\.."
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (!(Test-Path $python)) {
  throw 'Backend virtual environment missing. Run scripts/setup_windows.ps1 first.'
}

Push-Location $backend
try {
  & $python -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
} finally {
  Pop-Location
}

Push-Location $frontend
try {
  npm test
  if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }

  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally {
  Pop-Location
}

Write-Host 'All checks passed.'
