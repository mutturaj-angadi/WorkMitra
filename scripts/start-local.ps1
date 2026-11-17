[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$StatePath = Join-Path $PSScriptRoot '.local-processes.json'
$LogRoot = Join-Path $ProjectRoot 'logs\local'
$ApiUrl = 'http://127.0.0.1:8000'
$UiUrl = 'http://127.0.0.1:5173'

function Get-PortListeners([int]$Port) {
    try {
        return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop)
    } catch {
        return @()
    }
}

function Test-Http([string]$Url) {
    try {
        $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

$Python = Get-Command python -ErrorAction SilentlyContinue
$Node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $Python) { throw 'Python was not found on PATH. Install Python 3.11+ and reopen PowerShell.' }
if (-not $Node) { throw 'Node.js was not found on PATH. Install Node.js 22+ and reopen PowerShell.' }
if (-not (Test-Path (Join-Path $ProjectRoot '.env'))) { throw 'Missing .env. Copy .env.example to .env and select LLM_PROVIDER explicitly.' }
if (-not (Test-Path (Join-Path $FrontendRoot 'node_modules\vite\bin\vite.js'))) { throw 'Frontend dependencies are missing. Run npm.cmd ci from the frontend directory.' }

Push-Location $ProjectRoot
try {
    $Config = & $Python.Source -c "from backend.config import get_settings; from backend.database import engine; s=get_settings(); print('provider='+s.llm_provider); print('model='+str(s.google_model or 'none')); print('database='+engine.dialect.name); print('langsmith_tracing='+str(s.langchain_tracing_v2).lower())"
    if ($LASTEXITCODE -ne 0) { throw 'Environment configuration is invalid. Check provider/model and key presence without printing key values.' }
    $Config | ForEach-Object { Write-Host $_ }
} finally {
    Pop-Location
}

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
$Started = @()
function Save-StartedProcesses {
    if ($Started.Count -gt 0) {
        $Started | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding utf8
    }
}

$ApiListeners = Get-PortListeners 8000
if ($ApiListeners.Count -gt 0) {
    if (-not (Test-Http "$ApiUrl/api/v1/health")) {
        $owners = ($ApiListeners.OwningProcess | Sort-Object -Unique) -join ', '
        throw "Port 8000 is already used by PID(s) $owners, but this is not the project API. Stop the owning app yourself or configure a free port."
    }
    Write-Host "API already responds at $ApiUrl; reusing it."
} else {
    $ApiOut = Join-Path $LogRoot 'api.stdout.log'
    $ApiErr = Join-Path $LogRoot 'api.stderr.log'
    $ApiProcess = Start-Process -FilePath $Python.Source -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru
    $Started += [pscustomobject]@{ role='api'; pid=$ApiProcess.Id; started=$ApiProcess.StartTime.ToUniversalTime().ToString('o'); started_ticks=$ApiProcess.StartTime.ToUniversalTime().ToFileTimeUtc(); image=$Python.Source; signature='backend.main:app --host 127.0.0.1 --port 8000' }
    Save-StartedProcesses
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if ($ApiProcess.HasExited) { break }
        if (Test-Http "$ApiUrl/api/v1/ready") { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) {
        Stop-Process -Id $ApiProcess.Id -Force -ErrorAction SilentlyContinue
        if (Test-Path $ApiErr) { Get-Content $ApiErr -Tail 25 }
        throw 'Backend failed to become ready. Review logs/local/api.stderr.log.'
    }
}

$UiListeners = Get-PortListeners 5173
if ($UiListeners.Count -gt 0) {
    if (-not (Test-Http $UiUrl)) {
        $owners = ($UiListeners.OwningProcess | Sort-Object -Unique) -join ', '
        throw "Port 5173 is already used by PID(s) $owners, but the Vite page did not respond. Stop the owning app yourself or configure a free port."
    }
    Write-Host "Frontend already responds at $UiUrl; reusing it."
} else {
    $UiOut = Join-Path $LogRoot 'frontend.stdout.log'
    $UiErr = Join-Path $LogRoot 'frontend.stderr.log'
    $ViteEntry = Join-Path $FrontendRoot 'node_modules\vite\bin\vite.js'
    $UiProcess = Start-Process -FilePath $Node.Source -ArgumentList @("`"$ViteEntry`"",'--host','127.0.0.1') -WorkingDirectory $FrontendRoot -WindowStyle Hidden -RedirectStandardOutput $UiOut -RedirectStandardError $UiErr -PassThru
    $Started += [pscustomobject]@{ role='frontend'; pid=$UiProcess.Id; started=$UiProcess.StartTime.ToUniversalTime().ToString('o'); started_ticks=$UiProcess.StartTime.ToUniversalTime().ToFileTimeUtc(); image=$Node.Source; signature='node_modules\vite\bin\vite.js --host 127.0.0.1' }
    Save-StartedProcesses
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if ($UiProcess.HasExited) { break }
        if (Test-Http $UiUrl) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) {
        Stop-Process -Id $UiProcess.Id -Force -ErrorAction SilentlyContinue
        if (Test-Path $UiErr) { Get-Content $UiErr -Tail 25 }
        throw 'Frontend failed to become ready. Review logs/local/frontend.stderr.log.'
    }
}

Save-StartedProcesses
Write-Host "Local app is ready:"
Write-Host "  UI:       $UiUrl"
Write-Host "  API docs: $ApiUrl/docs"
if ($Started.Count -gt 0) {
    Write-Host 'Processes started by this script:'
    $Started | ForEach-Object { Write-Host "  $($_.role): PID $($_.pid)" }
}
Write-Host "Logs: $LogRoot"
