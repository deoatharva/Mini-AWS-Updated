$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot\.."
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'

Write-Host 'Checking prerequisites...'
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
  throw 'Node.js LTS is required. Install it from https://nodejs.org/ and run this script again.'
}

if (!(Test-Path $venvPython)) {
  Write-Host 'Creating the backend virtual environment...'
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue

  if ($pyLauncher) {
    & py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    & py -3 -m venv (Join-Path $backend '.venv')
  } elseif ($pythonCommand) {
    & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    & python -m venv (Join-Path $backend '.venv')
  } else {
    throw 'Python 3.11 or newer was not found. Install it from https://www.python.org/ and run this script again.'
  }
}

Write-Host 'Installing backend dependencies...'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $backend 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

$envFile = Join-Path $backend '.env'
if (!(Test-Path $envFile)) {
  Copy-Item (Join-Path $backend '.env.example') $envFile
  $secret = & $venvPython -c "import secrets; print(secrets.token_urlsafe(48))"
  (Get-Content $envFile) -replace '^SECRET_KEY=.*$', "SECRET_KEY=$secret" |
    Set-Content -Encoding ascii $envFile
  Write-Host 'Created backend/.env with a generated SECRET_KEY.'
} else {
  Write-Host 'backend/.env already exists; leaving it unchanged.'
}

Write-Host 'Installing frontend dependencies...'
Push-Location $frontend
try {
  npm install
  if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
  $frontendEnv = Join-Path $frontend '.env.local'
  if (!(Test-Path $frontendEnv)) {
    Copy-Item (Join-Path $frontend '.env.example') $frontendEnv
    Write-Host 'Created frontend/.env.local.'
  }
} finally {
  Pop-Location
}

Write-Host ''
Write-Host 'Setup finished. Start the lab with .\scripts\start_all.ps1'
Write-Host 'Or open two terminals and run start_backend.ps1 and start_frontend.ps1.'
