# Removes the extracted binary. Credentials in %USERPROFILE%\.config\zsp
# are deliberately left alone — uninstalling a tool should not destroy the
# user's saved login. Run `zsp logout` first to remove those.

$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Get-ChildItem -Path $toolsDir -Filter 'zsp.exe' -Recurse |
  ForEach-Object { Remove-Item $_.FullName -Force }

Write-Host "zsp removed. Credentials remain in ~/.config/zsp (delete manually if unwanted)."
