[CmdletBinding()]
param(
    [string]$DeployHost = '157.230.35.21',
    [string]$User = 'root',
    [int]$Port = 22,
    [string]$DeployDir = '/root/checkcheck',
    [string]$SshKeyPath = (Join-Path $PSScriptRoot '..\keys\do_checkcheck'),
    [string]$PublicHealthUrl = 'https://tscode.com.br/api/health',
    [string]$PublicAdminUrl = 'https://tscode.com.br/checking/admin',
    [switch]$Execute,
    [switch]$SkipPublicAdminMarkupCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$embeddedHostKeys = @(
    '157.230.35.21 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILcKvmHEtkkl9nI02Ds50toJUbMM4LFIWF011kR/Sq8k'
)

function ConvertTo-BashSingleQuotedLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)

    $singleQuoteEscape = [string]([char]39) + '"' + [string]([char]39) + '"' + [string]([char]39)
    return "'" + $Value.Replace("'", $singleQuoteEscape) + "'"
}

function Invoke-Stage8HttpCheck {
    param([Parameter(Mandatory = $true)][string]$Url)

    return Invoke-WebRequest -Uri $Url -UseBasicParsing
}

$resolvedKeyPath = (Resolve-Path -LiteralPath $SshKeyPath).Path
$sshPath = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
if (-not (Test-Path -LiteralPath $sshPath)) {
    throw "ssh.exe nao encontrado em $sshPath"
}

Write-Host "== public_health =="
$healthResponse = Invoke-Stage8HttpCheck -Url $PublicHealthUrl
Write-Host $healthResponse.Content

Write-Host "== public_admin_markup =="
$adminResponse = Invoke-Stage8HttpCheck -Url $PublicAdminUrl
$hasReportsTab = $adminResponse.Content -match 'data-tab="relatorios"'
$hasReportsSearch = $adminResponse.Content -match 'id="reportsSearchChave"'
Write-Host ("reports_tab_present={0}" -f $hasReportsTab.ToString().ToLowerInvariant())
Write-Host ("reports_search_present={0}" -f $hasReportsSearch.ToString().ToLowerInvariant())

if ((-not $SkipPublicAdminMarkupCheck) -and $Execute -and (-not ($hasReportsTab -and $hasReportsSearch))) {
    throw 'O admin publico ainda nao exibe a aba Relatorios. Publique o frontend/backend desta demanda antes de executar a limpeza remota.'
}

if ((-not $hasReportsTab) -or (-not $hasReportsSearch)) {
    Write-Warning 'O admin publico ainda nao exibe os marcadores da aba Relatorios. O modo dry-run continua permitido, mas o cleanup remoto deve permanecer bloqueado ate o deploy desta demanda.'
}

$executeCleanup = if ($Execute) { '1' } else { '0' }
$remoteScript = @"
set -euo pipefail
DEPLOY_DIR=$(ConvertTo-BashSingleQuotedLiteral -Value $DeployDir)
EXECUTE_CLEANUP=$executeCleanup
cd "`$DEPLOY_DIR"
if [ ! -f .env ]; then
    echo "Arquivo .env nao encontrado em `$DEPLOY_DIR" >&2
  exit 1
fi
echo "== internal_health =="
curl -fsS http://127.0.0.1:8000/api/health
echo
echo "== compose_ps =="
docker compose ps
echo "== check_events_before =="
before_count=`$(docker compose exec -T db psql -U postgres -d checking -Atc "SELECT COUNT(*) FROM check_events;")
echo "`$before_count"
if [ "`$EXECUTE_CLEANUP" != "1" ]; then
  echo "cleanup_mode=dry-run"
  exit 0
fi
echo "== deleting_check_events =="
docker compose exec -T db psql -U postgres -d checking -c "DELETE FROM check_events;"
echo "== check_events_after =="
after_count=`$(docker compose exec -T db psql -U postgres -d checking -Atc "SELECT COUNT(*) FROM check_events;")
echo "`$after_count"
if [ "`$after_count" != "0" ]; then
  echo "Cleanup de check_events nao zerou a tabela." >&2
  exit 1
fi
echo "cleanup_mode=executed"
echo "manual_followup=validar_fluxos_RFID_mobile_web_e_confirmar_ausencia_de_provider_em_check_events"
"@
$remoteScript = $remoteScript -replace "`r`n", "`n"

$knownHosts = [System.IO.Path]::GetTempFileName()
Set-Content -Path $knownHosts -Value ($embeddedHostKeys -join [Environment]::NewLine) -Encoding ascii

try {
    $sshArgs = @(
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=yes',
        '-o', ("UserKnownHostsFile={0}" -f $knownHosts),
        '-o', 'IdentitiesOnly=yes',
        '-i', $resolvedKeyPath,
        '-p', $Port,
        ("{0}@{1}" -f $User, $DeployHost),
        ("bash -lc {0}" -f (ConvertTo-BashSingleQuotedLiteral -Value $remoteScript))
    )

    & $sshPath @sshArgs
}
finally {
    Remove-Item $knownHosts -Force -ErrorAction SilentlyContinue
}