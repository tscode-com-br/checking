param(
    [string]$BuildName = "1.4.1",
    [int]$BuildNumber = 16,
    [switch]$SkipBuild,
    [switch]$RunConnectedTests
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "release-artifact-utils.ps1")

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Test-CheckingKeystoreProperties -ProjectRoot $projectRoot | Out-Null

Push-Location $projectRoot
try {
    Write-Host "[1/5] Unit tests."
    Invoke-CheckingGradle `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber `
        -Tasks @("testDebugUnitTest", "--rerun-tasks")

    Write-Host "[2/5] Lint."
    Invoke-CheckingGradle `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber `
        -Tasks @("lintDebug")

    Write-Host "[3/5] Instrumented-test APK compilation."
    Invoke-CheckingGradle `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber `
        -Tasks @("assembleDebugAndroidTest")

    if ($RunConnectedTests) {
        Write-Host "[4/5] Connected Android tests."
        Invoke-CheckingGradle `
            -ProjectRoot $projectRoot `
            -BuildName $BuildName `
            -BuildNumber $BuildNumber `
            -Tasks @("connectedDebugAndroidTest")
    } else {
        Write-Host "[4/5] Connected Android tests skipped. Re-run with -RunConnectedTests on Android 13/14/15+ devices."
    }

    if ($SkipBuild) {
        Write-Host "[5/5] Release build skipped by -SkipBuild."
    } else {
        Write-Host "[5/5] Signed release AAB."
        Invoke-CheckingGradle `
            -ProjectRoot $projectRoot `
            -BuildName $BuildName `
            -BuildNumber $BuildNumber `
            -Tasks @("bundleRelease")
        Write-Host "AAB generated at: app/build/outputs/bundle/release/app-release.aab"
    }

    $artifactRoot = Export-CheckingReleaseArtifacts `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber
    Write-Host "Release artifacts archived at: $artifactRoot"
}
finally {
    Pop-Location
}

