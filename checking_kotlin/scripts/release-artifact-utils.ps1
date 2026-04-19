function Export-CheckingReleaseArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,

        [Parameter(Mandatory = $true)]
        [string]$BuildName,

        [Parameter(Mandatory = $true)]
        [int]$BuildNumber
    )

    $bundleSourcePath = Join-Path $ProjectRoot "app\build\outputs\bundle\release\app-release.aab"
    $mappingSourceDirectory = Join-Path $ProjectRoot "app\build\outputs\mapping\release"
    $mappingSourcePath = Join-Path $mappingSourceDirectory "mapping.txt"

    if (-not (Test-Path $bundleSourcePath)) {
        throw "Release AAB not found: $bundleSourcePath"
    }

    if (-not (Test-Path $mappingSourcePath)) {
        throw "R8 mapping file not found: $mappingSourcePath"
    }

    $releaseId = "$BuildName+$BuildNumber"
    $artifactRoot = Join-Path $ProjectRoot "build\release-artifacts\$releaseId"
    $mappingDestinationDirectory = Join-Path $artifactRoot "r8-mapping"
    $bundleDestinationPath = Join-Path $artifactRoot "app-release.aab"
    $metadataPath = Join-Path $artifactRoot "release-metadata.json"

    if (Test-Path $artifactRoot) {
        Remove-Item -Path $artifactRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Path $mappingDestinationDirectory -Force | Out-Null
    Copy-Item -Path $bundleSourcePath -Destination $bundleDestinationPath -Force
    Copy-Item -Path (Join-Path $mappingSourceDirectory "*") -Destination $mappingDestinationDirectory -Recurse -Force

    $metadata = [ordered]@{
        releaseId = $releaseId
        buildName = $BuildName
        buildNumber = $BuildNumber
        archivedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
        archivedBundle = $bundleDestinationPath
        archivedMappingFile = Join-Path $mappingDestinationDirectory "mapping.txt"
        sourceBundle = $bundleSourcePath
        sourceMappingDirectory = $mappingSourceDirectory
    }

    $metadata |
        ConvertTo-Json -Depth 3 |
        Set-Content -Path $metadataPath -Encoding UTF8

    return $artifactRoot
}

function Parse-KeyValueFile {
    param([string]$Path)

    $values = @{}
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith("#")) { continue }

        $split = $trimmed -split "=", 2
        if ($split.Count -ne 2) { continue }

        $key = $split[0].Trim()
        $value = $split[1].Trim()
        $values[$key] = $value
    }
    return $values
}

function Test-CheckingKeystoreProperties {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $keystorePropsPath = Join-Path $ProjectRoot "keystore.properties"

    if (-not (Test-Path $keystorePropsPath)) {
        throw "Missing keystore.properties. Copy keystore.properties.example and fill it with real upload key values."
    }

    $props = Parse-KeyValueFile -Path $keystorePropsPath
    $requiredKeys = @("storeFile", "storePassword", "keyAlias", "keyPassword")

    foreach ($requiredKey in $requiredKeys) {
        if (-not $props.ContainsKey($requiredKey) -or [string]::IsNullOrWhiteSpace($props[$requiredKey])) {
            throw "Missing required key '$requiredKey' in keystore.properties"
        }
        if ($props[$requiredKey] -eq "change-me") {
            throw "keystore.properties still contains placeholder value for '$requiredKey'"
        }
    }

    $storeFilePath = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $props["storeFile"]))
    if (-not (Test-Path $storeFilePath)) {
        throw "Configured storeFile does not exist: $storeFilePath"
    }

    return $props
}

function Invoke-CheckingGradle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,

        [Parameter(Mandatory = $true)]
        [string]$BuildName,

        [Parameter(Mandatory = $true)]
        [int]$BuildNumber,

        [Parameter(Mandatory = $true)]
        [string[]]$Tasks
    )

    $gradlew = Join-Path $ProjectRoot "gradlew.bat"
    $gradleArgs = @(
        "-Pchecking.versionName=$BuildName",
        "-Pchecking.versionCode=$BuildNumber"
    ) + $Tasks

    & $gradlew @gradleArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle failed with exit code $LASTEXITCODE while running: $($Tasks -join ' ')"
    }
}

