# Run once as administrator. Enables the two Windows prerequisites without rebooting.
param([string]$ReportPath)
$ErrorActionPreference = 'Stop'
$workspacePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $ReportPath) { $ReportPath = Join-Path $workspacePath ('tmp/wsl-features-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json') }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this script as administrator.' }
if (Test-Path -LiteralPath $ReportPath) { throw 'Choose a new report path.' }
$report = @{ started_at = [DateTime]::UtcNow.ToString('o'); features = @(); reboot_required = $false; automatic_reboot = $false }
try {
    foreach ($featureName in @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')) {
        $before = Get-WindowsOptionalFeature -Online -FeatureName $featureName
        if ($before.State -eq 'Enabled') { $result = $null }
        elseif ($before.State -eq 'EnablePending') { $report.reboot_required = $true; $result = $null }
        else {
            $result = Enable-WindowsOptionalFeature -Online -FeatureName $featureName -All -NoRestart
            if ($result.RestartNeeded) { $report.reboot_required = $true }
        }
        $after = Get-WindowsOptionalFeature -Online -FeatureName $featureName
        $report.features += @{ name = $featureName; before = $before.State.ToString(); after = $after.State.ToString() }
    }
    $report.completed = $true
} catch {
    $report.completed = $false
    $report.error = $_.Exception.Message
} finally {
    $report.completed_at = [DateTime]::UtcNow.ToString('o')
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
if ($report.reboot_required) { exit 3010 }
