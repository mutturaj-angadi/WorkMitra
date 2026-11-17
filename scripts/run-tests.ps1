$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Get-Command python -ErrorAction SilentlyContinue
$Npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $Python) { throw 'Python was not found on PATH.' }
if (-not $Npm) { throw 'npm.cmd was not found on PATH.' }

Push-Location $ProjectRoot
try {
    & $Python.Source -m pytest -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Pytest failed.' }
    & $Python.Source -m ruff check backend
    if ($LASTEXITCODE -ne 0) { throw 'Ruff lint failed.' }
    & $Python.Source -m ruff format --check backend
    if ($LASTEXITCODE -ne 0) { throw 'Ruff formatting check failed.' }
    & $Python.Source -m compileall -q backend
    if ($LASTEXITCODE -ne 0) { throw 'Python compilation failed.' }
    & $Python.Source -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
    Push-Location (Join-Path $ProjectRoot 'frontend')
    try {
        & $Npm.Source run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}
