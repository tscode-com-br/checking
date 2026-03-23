param(
  [Parameter(Mandatory = $true)] [string]$ServerHost,
  [Parameter(Mandatory = $true)] [string]$User,
  [Parameter(Mandatory = $true)] [string]$KeyPath,
  [string]$RemoteDir = "~/checkcheck"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
  throw "SSH key not found at: $KeyPath"
}

if (-not (Test-Path ".\\.env")) {
  throw "Missing .env in project root. Create it from deploy/.env.production.example before deploy."
}

Write-Host "[1/4] Uploading project files..."
$tarCmd = "tar --exclude=.git --exclude=.venv --exclude=.pytest_cache --exclude=checking.db --exclude=test_checking.db -czf - ."
cmd /c $tarCmd | ssh -i $KeyPath "$User@$ServerHost" "mkdir -p $RemoteDir && tar -xzf - -C $RemoteDir"

Write-Host "[2/4] Uploading .env..."
scp -i $KeyPath .env "$User@$ServerHost`:$RemoteDir/.env"

Write-Host "[3/4] Starting containers..."
ssh -i $KeyPath "$User@$ServerHost" "cd $RemoteDir && docker compose pull && docker compose up -d --build"

Write-Host "[4/4] Health check..."
ssh -i $KeyPath "$User@$ServerHost" "curl -fsS http://127.0.0.1:8000/api/health || true"

Write-Host "Deploy completed."
