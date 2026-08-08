param([string]$InstallDir = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$envFile = Join-Path $InstallDir '.env'
$example = Join-Path $InstallDir '.env.example'
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $example -Destination $envFile
}
Start-Process notepad.exe -ArgumentList ('"' + $envFile + '"') -Wait
[System.Windows.Forms.MessageBox]::Show(
    "配置已保存。请确认 PostgreSQL 已启动，并填写所有必需密码和 API Key，然后双击“智屿”启动。",
    "智屿配置工具"
) | Out-Null
