$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$specFile = Join-Path $projectRoot "client\RealDataViewClient.spec"
$clientConfig = Join-Path $projectRoot "client\config.json"
$clientIcons = Join-Path $projectRoot "client\icons"
$distDir = Join-Path $projectRoot "dist\client"
$workDir = Join-Path $projectRoot "build\client"
$zipFile = Join-Path $projectRoot "dist\DataViewer-Windows-x64.zip"
$exeFile = Join-Path $distDir "DataViewer.exe"
$legacyExeFile = Join-Path $distDir "RealDataViewClient.exe"
$legacyZipFile = Join-Path $projectRoot "dist\RealDataViewClient-Windows-x64.zip"

$runningClient = Get-Process -Name "DataViewer", "RealDataViewClient" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -in @($exeFile, $legacyExeFile) }
if ($runningClient) {
    throw "DataViewer is running. Close the client before building."
}

foreach ($legacyFile in @($legacyExeFile, $legacyZipFile)) {
    if (Test-Path -LiteralPath $legacyFile) {
        Remove-Item -LiteralPath $legacyFile -Force
    }
}

Write-Host "Building DataViewer client..."
python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $distDir `
    --workpath $workDir `
    $specFile

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Copy-Item -LiteralPath $clientConfig -Destination (Join-Path $distDir "config.json") -Force
Copy-Item -LiteralPath $clientIcons -Destination (Join-Path $distDir "icons") -Recurse -Force

if (Test-Path -LiteralPath $zipFile) {
    Remove-Item -LiteralPath $zipFile -Force
}

Compress-Archive `
    -Path (Join-Path $distDir "*") `
    -DestinationPath $zipFile `
    -CompressionLevel Optimal

Write-Host "Build completed:"
Write-Host "  EXE: $exeFile"
Write-Host "  ZIP: $zipFile"
