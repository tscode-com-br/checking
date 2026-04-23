param(
  [ValidateSet("text", "json")]
  [string]$Format = "text",
  [string]$OutputPath,
  [switch]$IncludeValid,
  [switch]$FailOnWarnings,
  [int]$DbReadyAttempts = 30,
  [int]$DbReadyDelaySeconds = 2,
  [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-ComposeInvocation {
  if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    return @{
      FilePath = "docker-compose"
      PrefixArgs = @()
      Description = "docker-compose"
    }
  }

  if (Get-Command docker -ErrorAction SilentlyContinue) {
    return @{
      FilePath = "docker"
      PrefixArgs = @("compose")
      Description = "docker compose"
    }
  }

  if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $wslDockerReady = $false
    try {
      & wsl -d Ubuntu -- docker compose version *> $null
      $wslDockerReady = ($LASTEXITCODE -eq 0)
    }
    catch {
      $wslDockerReady = $false
    }

    if ($wslDockerReady -or $WhatIfOnly) {
      return @{
        FilePath = "wsl"
        PrefixArgs = @("-d", "Ubuntu", "--", "docker", "compose")
        Description = "wsl -d Ubuntu -- docker compose"
      }
    }
  }

  if ($WhatIfOnly) {
    return @{
      FilePath = "wsl"
      PrefixArgs = @("-d", "Ubuntu", "--", "docker", "compose")
      Description = "wsl -d Ubuntu -- docker compose"
    }
  }

  throw "Neither native Docker Compose nor the Ubuntu WSL Docker Compose backend is available. Install Docker Desktop or provision Docker inside the Ubuntu WSL distro before running the compose audit."
}

function Format-CommandText {
  param(
    [hashtable]$Compose,
    [string[]]$ComposeArgs
  )

  return (($Compose.FilePath) + " " + ((@($Compose.PrefixArgs) + $ComposeArgs) -join " ")).Trim()
}

function Invoke-Compose {
  param(
    [hashtable]$Compose,
    [string[]]$ComposeArgs,
    [switch]$CaptureOutput
  )

  $display = Format-CommandText -Compose $Compose -ComposeArgs $ComposeArgs
  if ($WhatIfOnly) {
    Write-Host "[what-if] $display"
    if ($CaptureOutput) {
      return ""
    }
    return
  }

  $fullArgs = @($Compose.PrefixArgs) + $ComposeArgs
  if ($CaptureOutput) {
    $captured = & $Compose.FilePath @fullArgs 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($captured | Out-String)
    if ($exitCode -ne 0) {
      if ($text) {
        [Console]::Error.Write($text)
      }
      throw "Compose command failed with exit code ${exitCode}: $display"
    }
    return $text
  }

  & $Compose.FilePath @fullArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Compose command failed with exit code ${LASTEXITCODE}: $display"
  }
}

function Wait-ComposeDatabase {
  param([hashtable]$Compose)

  $probeArgs = @(
    "exec",
    "-T",
    "db",
    "sh",
    "-lc",
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
  )

  if ($WhatIfOnly) {
    Write-Host "[what-if] wait for compose Postgres readiness via pg_isready"
    return
  }

  for ($attempt = 1; $attempt -le $DbReadyAttempts; $attempt++) {
    & $Compose.FilePath @($Compose.PrefixArgs + $probeArgs) *> $null
    if ($LASTEXITCODE -eq 0) {
      return
    }

    Write-Host "Waiting for compose Postgres ($attempt/$DbReadyAttempts)..."
    Start-Sleep -Seconds $DbReadyDelaySeconds
  }

  throw "Postgres service 'db' did not become ready after $DbReadyAttempts attempts."
}

function Resolve-ComposeWorkspacePath {
  param(
    [hashtable]$Compose,
    [string]$WindowsPath
  )

  if ($Compose.FilePath -ne "wsl") {
    return $WindowsPath
  }

  if ($WhatIfOnly) {
    $normalizedPath = $WindowsPath -replace "\\", "/"
    if ($normalizedPath -match "^(?<drive>[A-Za-z]):(?<rest>/.*)$") {
      return "/mnt/$($matches['drive'].ToLower())$($matches['rest'])"
    }
    return $normalizedPath
  }

  $normalizedPath = $WindowsPath -replace "\\", "/"
  if ($normalizedPath -match "^(?<drive>[A-Za-z]):(?<rest>/.*)$") {
    return "/mnt/$($matches['drive'].ToLower())$($matches['rest'])"
  }

  throw "Failed to convert project path '$WindowsPath' to a WSL mount path."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$compose = Resolve-ComposeInvocation
$workspaceMountPath = Resolve-ComposeWorkspacePath -Compose $compose -WindowsPath $projectRoot

$auditFormat = $Format

$envNamesToClear = @(
  "DATABASE_URL",
  "POSTGRES_DB",
  "POSTGRES_USER",
  "POSTGRES_PASSWORD",
  "POSTGRES_PORT"
)
$savedEnvValues = @{}

Push-Location $projectRoot
try {
  if (-not (Test-Path ".\\.env")) {
    throw "Missing .env in project root. Create it before running the compose audit."
  }

  foreach ($envName in $envNamesToClear) {
    if (Test-Path "Env:$envName") {
      $savedEnvValues[$envName] = (Get-Item "Env:$envName").Value
      Remove-Item "Env:$envName"
    }
    else {
      $savedEnvValues[$envName] = $null
    }
  }

  Invoke-Compose -Compose $compose -ComposeArgs @("up", "-d", "db")
  Wait-ComposeDatabase -Compose $compose

  Invoke-Compose -Compose $compose -ComposeArgs @("build", "app")

  $auditArgs = @(
    "run",
    "--rm",
    "--no-deps",
    "-v", "${workspaceMountPath}:/workspace",
    "app",
    "python",
    "/workspace/scripts/audit_locations.py",
    "--format", $auditFormat
  )
  if ($IncludeValid) {
    $auditArgs += "--include-valid"
  }
  if ($FailOnWarnings) {
    $auditArgs += "--fail-on-warnings"
  }

  $auditOutput = Invoke-Compose -Compose $compose -ComposeArgs $auditArgs -CaptureOutput
  if ($OutputPath) {
    Set-Content -Path $OutputPath -Value $auditOutput -Encoding UTF8
  }
  if ($auditOutput) {
    [Console]::Out.Write($auditOutput)
  }
}
finally {
  foreach ($envName in $envNamesToClear) {
    $previousValue = $savedEnvValues[$envName]
    if ($null -eq $previousValue) {
      Remove-Item "Env:$envName" -ErrorAction SilentlyContinue
    }
    else {
      Set-Item "Env:$envName" -Value $previousValue
    }
  }
  Pop-Location
}