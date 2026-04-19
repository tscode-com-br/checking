param(
    [string]$BuildName = "1.4.1",
    [int]$BuildNumber = 16,
    [switch]$SkipQualityChecks
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "release-artifact-utils.ps1")

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Test-CheckingKeystoreProperties -ProjectRoot $projectRoot | Out-Null

Push-Location $projectRoot
try {
    if ($SkipQualityChecks) {
        Write-Host "[1/2] Quality checks skipped by -SkipQualityChecks."
    } else {
        Write-Host "[1/2] Running unit tests, lint and instrumented-test APK build."
        Invoke-CheckingGradle `
            -ProjectRoot $projectRoot `
            -BuildName $BuildName `
            -BuildNumber $BuildNumber `
            -Tasks @("testDebugUnitTest", "lintDebug", "assembleDebugAndroidTest")
    }

    Write-Host "[2/2] Building signed release AAB for $BuildName+$BuildNumber."
    Invoke-CheckingGradle `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber `
        -Tasks @("bundleRelease")

    Write-Host "AAB generated at: app/build/outputs/bundle/release/app-release.aab"
    $artifactRoot = Export-CheckingReleaseArtifacts `
        -ProjectRoot $projectRoot `
        -BuildName $BuildName `
        -BuildNumber $BuildNumber
    Write-Host "Release artifacts archived at: $artifactRoot"
}
finally {
    Pop-Location
}

