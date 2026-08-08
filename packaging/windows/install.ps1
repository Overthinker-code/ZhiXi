param(
    [Parameter(Mandatory=$true)][string]$Payload,
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'ZhiYu')
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

try {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $stage = Join-Path $env:TEMP ('zhiyu-install-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    Expand-Archive -LiteralPath $Payload -DestinationPath $stage -Force

    # Preserve the user's private configuration across upgrades.
    $privateConfig = Join-Path $InstallDir '.env'
    Get-ChildItem -LiteralPath $stage -Force | ForEach-Object {
        $target = Join-Path $InstallDir $_.Name
        if ($_.Name -eq '.env') { return }
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
        Move-Item -LiteralPath $_.FullName -Destination $target -Force
    }
    Remove-Item -LiteralPath $stage -Recurse -Force

    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcut = $shell.CreateShortcut((Join-Path $desktop '智屿.lnk'))
    $shortcut.TargetPath = Join-Path $InstallDir '智屿.exe'
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = (Join-Path $InstallDir '智屿.exe') + ',0'
    $shortcut.Save()

    $configShortcut = $shell.CreateShortcut((Join-Path $desktop '智屿配置工具.lnk'))
    $configShortcut.TargetPath = 'powershell.exe'
    $configShortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $InstallDir 'configure-zhiyu.ps1') + '" -InstallDir "' + $InstallDir + '"'
    $configShortcut.WorkingDirectory = $InstallDir
    $configShortcut.Save()

    if (-not (Test-Path -LiteralPath $privateConfig)) {
        Copy-Item -LiteralPath (Join-Path $InstallDir '.env.example') -Destination $privateConfig
        [System.Windows.Forms.MessageBox]::Show(
            "智屿已安装到：`n$InstallDir`n`n首次运行前，请通过桌面的“智屿配置工具”填写数据库和模型配置。安装包未包含任何真实密钥。",
            '智屿安装完成', 'OK', 'Information'
        ) | Out-Null
        Start-Process notepad.exe -ArgumentList ('"' + $privateConfig + '"')
    } else {
        [System.Windows.Forms.MessageBox]::Show("智屿升级完成，原有私密配置已保留。", '智屿', 'OK', 'Information') | Out-Null
    }
} catch {
    [System.Windows.Forms.MessageBox]::Show("安装失败：`n" + $_.Exception.Message, '智屿安装程序', 'OK', 'Error') | Out-Null
    exit 1
}
