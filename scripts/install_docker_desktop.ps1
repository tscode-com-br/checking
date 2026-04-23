param(
  [switch]$WhatIfOnly,
  [switch]$ForceDownload,
  [string]$ResultFile
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Test-IsElevated {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-InstallResult {
  param(
    [string]$Message,
    [int]$ExitCode = 0
  )

  $payload = [PSCustomObject]@{
    message = $Message
    exitCode = $ExitCode
  }

  if ($ResultFile) {
    $payload | ConvertTo-Json -Compress | Set-Content -Path $ResultFile -Encoding UTF8
  }

  Write-Output $Message
  exit $ExitCode
}

function Resolve-InstallerPath {
  $installerPath = Join-Path $env:TEMP 'DockerDesktopInstaller.exe'
  if ((-not (Test-Path $installerPath)) -or $ForceDownload) {
    Invoke-WebRequest \
      -Uri 'https://desktop.docker.com/win/main/amd64/224270/Docker%20Desktop%20Installer.exe' \
      -OutFile $installerPath
  }
  return $installerPath
}

function Get-WslVersionText {
  try {
    return ((& wsl.exe --version 2>&1) | Out-String).Trim()
  }
  catch {
    return ''
  }
}

if (-not (Test-IsElevated)) {
  if ($WhatIfOnly) {
    Write-Output 'Would elevate and run the Docker Desktop installer with --backend=wsl-2 --accept-license --quiet.'
    exit 0
  }

  $effectiveResultFile = if ($ResultFile) {
    $ResultFile
  }
  else {
    Join-Path $env:TEMP ("docker_desktop_install_result_" + [guid]::NewGuid().ToString('N') + '.json')
  }

  $elevatedArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $PSCommandPath,
    '-ResultFile', $effectiveResultFile
  )
  if ($ForceDownload) {
    $elevatedArgs += '-ForceDownload'
  }

  try {
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $elevatedArgs -Wait | Out-Null
  }
  catch {
    throw 'Windows UAC elevation was cancelled or failed. Approve the administrator prompt to install Docker Desktop.'
  }

  if (-not (Test-Path $effectiveResultFile)) {
    throw 'The elevated installer did not return a result file. The installation may not have started or was interrupted.'
  }

  $result = Get-Content -Path $effectiveResultFile -Raw | ConvertFrom-Json
  Remove-Item $effectiveResultFile -Force -ErrorAction SilentlyContinue
  Write-Output $result.message
  exit ([int]$result.exitCode)
}

$wslVersion = Get-WslVersionText
if (-not $wslVersion) {
  Write-InstallResult \
    -Message 'WSL is not available on this machine. Install or update WSL first with an elevated `wsl --install` before installing Docker Desktop.' \
    -ExitCode 1
}

$installerPath = Resolve-InstallerPath
$installArgs = @(
  'install',
  '--quiet',
  '--accept-license',
  '--backend=wsl-2',
  '--no-windows-containers'
)

if ($WhatIfOnly) {
  Write-InstallResult \
    -Message ("Would run: `"$installerPath`" " + ($installArgs -join ' ')) \
    -ExitCode 0
}

$process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -PassThru -Wait
if ($process.ExitCode -ne 0) {
  Write-InstallResult \
    -Message ("Docker Desktop installer failed with exit code $($process.ExitCode).") \
    -ExitCode $process.ExitCode
}

$dockerDesktopExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$dockerCliExe = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'

if (-not (Test-Path $dockerDesktopExe) -or -not (Test-Path $dockerCliExe)) {
  Write-InstallResult \
    -Message 'Docker Desktop installer finished, but the expected executables were not found under C:\Program Files\Docker\Docker.' \
    -ExitCode 1
}

$groupNote = ''
try {
  $addGroupOutput = cmd.exe /c "net localgroup docker-users $env:USERNAME /add" 2>&1 | Out-String
  if ($addGroupOutput -match 'The command completed successfully') {
    $groupNote = ' Added the current user to docker-users.'
  }
}
catch {
  $groupNote = ''
}

Write-InstallResult \
  -Message ("Docker Desktop installed successfully at $dockerDesktopExe.$groupNote Open a new terminal or sign out and back in before using docker/compose.") \
  -ExitCode 0