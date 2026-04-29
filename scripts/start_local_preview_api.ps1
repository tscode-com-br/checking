param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8010,
  [string]$DatabaseFile = "preview_checking.db",
  [switch]$Reload,
  [switch]$SkipMigrate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
  throw "Python environment not found at '$pythonExe'. Activate/create .venv first."
}

$previousDatabaseUrl = $env:DATABASE_URL
$previousAppEnv = $env:APP_ENV

Push-Location $repoRoot
try {
  $env:DATABASE_URL = "sqlite+pysqlite:///./$DatabaseFile"
  $env:APP_ENV = "production"

  if (-not $SkipMigrate) {
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
      throw "Alembic upgrade failed with exit code $LASTEXITCODE."
    }
  }

  $uvicornArgs = @(
    "-m",
    "uvicorn",
    "sistema.app.main:app",
    "--host",
    $BindHost,
    "--port",
    [string]$Port
  )

  if ($Reload) {
    $uvicornArgs += "--reload"
  }

  Write-Host "Starting local preview API on http://${BindHost}:$Port using $DatabaseFile"
  Write-Host "DATABASE_URL=$($env:DATABASE_URL)"

  & $pythonExe @uvicornArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Uvicorn exited with code $LASTEXITCODE."
  }
}
finally {
  $env:DATABASE_URL = $previousDatabaseUrl
  $env:APP_ENV = $previousAppEnv
  Pop-Location
}