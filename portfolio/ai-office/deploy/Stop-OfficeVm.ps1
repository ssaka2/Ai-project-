# Azure Automation PowerShell runbook. Requires Az.Accounts and Az.Compute.
# The assigned role must be scoped to the one approved VM.
param(
    [Parameter(Mandatory=$true)][guid]$SubscriptionId,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_.()-]{1,90}$')][string]$ResourceGroupName,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]{1,64}$')][string]$VmName
)
$ErrorActionPreference = 'Stop'
Disable-AzContextAutosave -Scope Process | Out-Null
$context = (Connect-AzAccount -Identity).Context
$context = Set-AzContext -SubscriptionId $SubscriptionId -DefaultProfile $context
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VmName -Status -DefaultProfile $context
if ($vm.Statuses.Code -contains 'PowerState/deallocated') {
    Write-Output 'VM already deallocated.'
    return
}
# Do not use -StayProvisioned: it leaves compute resources allocated.
Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VmName -Force -DefaultProfile $context | Out-Null
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VmName -Status -DefaultProfile $context
if ($vm.Statuses.Code -notcontains 'PowerState/deallocated') {
    throw 'Deallocation was not confirmed. Operator intervention required.'
}
Write-Output 'VM deallocation confirmed.'
