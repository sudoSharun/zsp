# Installs the standalone zsp binary from GitHub Releases.
# Chocolatey users are not assumed to have Python.

$ErrorActionPreference = 'Stop'

$packageName = 'zsp'
$version     = '0.1.0'
$url64       = "https://github.com/sudoSharun/zsp/releases/download/v$version/zsp-$version-windows-x64.zip"
$toolsDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition

$packageArgs = @{
  packageName    = $packageName
  unzipLocation  = $toolsDir
  url64bit       = $url64
  # Replaced by the release workflow, which computes it from the built zip.
  checksum64     = 'REPLACE_WITH_WINDOWS_ZIP_SHA256'
  checksumType64 = 'sha256'
}

Install-ChocolateyZipPackage @packageArgs

# Chocolatey shims every .exe under tools/, which puts `zsp` on PATH.
Write-Host "zsp $version installed. Run 'zsp login' to authenticate." -ForegroundColor Green
