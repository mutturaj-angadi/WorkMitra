[CmdletBinding()]
param([switch]$ProbeProvider)

$ErrorActionPreference = 'Stop'
$ApiUrl = 'http://127.0.0.1:8000'
$UiUrl = 'http://127.0.0.1:5173'
try {
    $Health = Invoke-RestMethod "$ApiUrl/api/v1/health" -TimeoutSec 5
    $Ready = Invoke-RestMethod "$ApiUrl/api/v1/ready" -TimeoutSec 5
    $Settings = Invoke-RestMethod "$ApiUrl/api/v1/settings" -TimeoutSec 5
    $Provider = Invoke-RestMethod "$ApiUrl/api/v1/provider/health" -TimeoutSec 5
    $Ui = Invoke-WebRequest $UiUrl -UseBasicParsing -TimeoutSec 5
    [pscustomobject]@{
        Backend = $Health.status
        Database = $Settings.database_backend
        LegalCorpusReady = $Ready.legal_corpus_ready
        AdvisoryMode = $Ready.mode
        Provider = $Provider.provider
        Model = $Provider.model
        MockMode = $Provider.mock_mode_active
        TracingEnabled = $Provider.tracing_enabled
        LangSmithKeyConfigured = $Provider.langsmith_key_configured
        LastProviderProbeSucceeded = $Provider.last_probe_success
        FrontendStatusCode = $Ui.StatusCode
        ApiDocs = "$ApiUrl/docs"
        Frontend = $UiUrl
    } | Format-List
} catch {
    Write-Error 'Health checks failed. Start the local application and review logs/local.'
    exit 1
}

if ($ProbeProvider) {
    try {
        Invoke-RestMethod "$ApiUrl/api/v1/provider/check" -Method Post -TimeoutSec 55 | Format-List
    } catch {
        Write-Error 'Provider probe failed. The server returns only a sanitized failure type; review provider configuration and network access.'
        exit 1
    }
}
