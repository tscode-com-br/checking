param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

& $pythonExe (Join-Path $scriptDir "monitor_rfid_hid.py") @Arguments
$exitCode = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
exit $exitCode