param([int]$Port = 8501, [switch]$NoWorker)
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $projectRoot
try {
    if (-not $NoWorker) {
        python -B -m reqstudio.worker start
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Background worker did not start. Check CLI installation/login or start it from the UI.' }
    }
    python -m streamlit run (Join-Path $projectRoot 'streamlit_app.py') --server.address 127.0.0.1 --server.port $Port --server.fileWatcherType none --browser.gatherUsageStats false
} finally {
    Pop-Location
}
