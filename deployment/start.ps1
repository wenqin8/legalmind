param([string]$ProjectName = 'legalmind-m4')
$ErrorActionPreference = 'Stop'
$workspacePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $workspacePath
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $dockerLocations = @((Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin'), 'C:/Program Files/Docker/Docker/resources/bin')
        foreach ($dockerLocation in $dockerLocations) {
            if (Test-Path -LiteralPath (Join-Path $dockerLocation 'docker.exe')) { $env:PATH = $dockerLocation + ';' + $env:PATH; break }
        }
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop must be installed and running.' }
    if (-not (Test-Path -LiteralPath 'deployment/.env')) { throw 'Run deployment/init_env.py and configure deployment/.env first.' }
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is unavailable.' }
    docker compose --env-file deployment/.env -f compose.yml -p $ProjectName config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed validation.' }
    docker compose --env-file deployment/.env -f compose.yml -p $ProjectName up -d --build --wait --wait-timeout 1200
    if ($LASTEXITCODE -ne 0) { throw 'Application startup failed. Inspect service logs locally.' }
    Write-Output 'Application services are ready. Continue with the deployment acceptance script.'
} finally { Pop-Location }
