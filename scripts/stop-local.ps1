$ErrorActionPreference = 'Stop'
$StatePath = Join-Path $PSScriptRoot '.local-processes.json'
if (-not (Test-Path -LiteralPath $StatePath)) {
    Write-Host 'No processes started by scripts/start-local.ps1 are recorded.'
    exit 0
}

$Records = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $StatePath -Raw)
$Remaining = @()
foreach ($Record in $Records) {
    $Process = Get-Process -Id $Record.pid -ErrorAction SilentlyContinue
    if (-not $Process) {
        Write-Host "$($Record.role): PID $($Record.pid) is already stopped."
        continue
    }
    if ($Record.started_ticks) {
        $TimeMatches = [math]::Abs($Process.StartTime.ToUniversalTime().ToFileTimeUtc() - [int64]$Record.started_ticks) -lt 30000000
    } else {
        $RecordedStart = [DateTimeOffset]::Parse([string]$Record.started, [Globalization.CultureInfo]::InvariantCulture).UtcDateTime
        $TimeMatches = [math]::Abs(($Process.StartTime.ToUniversalTime() - $RecordedStart).TotalSeconds) -lt 3
    }
    $ImageMatches = $false
    if ($Record.image -and $Process.Path) {
        try {
            $ImageMatches = [string]::Equals(
                [IO.Path]::GetFullPath($Process.Path),
                [IO.Path]::GetFullPath([string]$Record.image),
                [StringComparison]::OrdinalIgnoreCase
            )
        } catch {
            $ImageMatches = $false
        }
    }
    if (-not ($ImageMatches -and $TimeMatches)) {
        Write-Warning "$($Record.role): PID $($Record.pid) no longer matches the recorded executable/start time; leaving it untouched."
        $Remaining += $Record
        continue
    }
    Stop-Process -Id $Record.pid -Force
    Write-Host "Stopped $($Record.role), PID $($Record.pid)."
}
if ($Remaining.Count -gt 0) {
    $Remaining | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding utf8
    Write-Warning 'Some processes were left untouched; their records remain for a later safe shutdown.'
} else {
    Remove-Item -LiteralPath $StatePath -Force
}
