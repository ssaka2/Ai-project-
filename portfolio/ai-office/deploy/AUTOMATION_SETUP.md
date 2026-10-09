# Alternative test shutdown safeguard

Status: prepared, not deployed or live-tested. No identity or role assignment has
been created by adding these files. The current VM is deallocated.

The built-in shutdown scheduler rejected Mexico Central as unsupported. A schedule
in Central US was also rejected because it must be colocated with its target VM.
Azure Automation is a separate service and runs its runbook against Azure Resource
Manager; the runbook does not need to run on the target VM.

## Exact access proposal

Create an Automation account in Central US (a region allowed by the observed
subscription policy), using a system-assigned managed identity. Register the
`AI Office VM Deallocator` custom role from `stop-vm-role.template.json` with the
actual subscription and resource group. Assign it to that identity **at the exact
resource ID of ssaka2-portfolio-vm**, never at subscription or resource-group
scope. The assignable scope in the definition is where the role may be assigned;
it is not a role assignment and grants no permissions itself.

The three allowed operations read VM metadata/power state and deallocate it.
There are no candidate-data, mailbox, secret-store, VM command execution, VM
creation, restart, resize, deletion, or role-administration permissions.

Creating this cloud identity and permission grant requires explicit approval.
The existing approval for a one-hour VM test does not silently grant a new
identity access to the subscription. Check Automation availability and account
usage/pricing before deployment; do not promise this is unconditionally free.

## Installation and acceptance gates

1. Create the Automation account and identity; do not start the VM yet.
2. Import compatible Az.Accounts and Az.Compute modules into its PowerShell
   runtime. Import and publish `Stop-OfficeVm.ps1`.
3. Apply the approved custom role assignment at the one VM resource ID. Wait for
   role propagation; never expand the role to fix a propagation delay.
4. Run the runbook against the already-deallocated VM. Confirm the job completes
   and prints `VM already deallocated.`. Inspect the actual role assignment scope.
5. Register a one-time UTC shutdown schedule before starting the test. Bind its
   SubscriptionId, ResourceGroupName, and VmName to the approved VM. Confirm the
   published runbook, enabled one-time schedule, parameters, and UTC deadline by
   reading them back. Missing modules, authorization, or schedule means no launch.
6. Set the deadline at most 50 minutes after test start, allowing a margin for the
   authorized one-hour session. Jobs can queue or fail: an operator must still
   verify the actual VM reaches `PowerState/deallocated`; a successful schedule
   creation is not a shutdown guarantee.
7. Start the existing VM, install the already-tested gateway and latest office,
   and verify external HTTPS, authentication, and synthetic saves. Stop and
   deallocate manually as soon as checks complete. Keep the one-time safeguard
   scheduled until deallocation is verified.
8. Verify the final power state and record the job result. Do not automatically
   restart the VM or turn the test into ongoing paid hosting.

Only after this test can ongoing hosting be planned with an explicit budget and
availability requirements. Single-operator HTTPS does not add candidate accounts,
automatic applications, mailbox OAuth, or autonomous staff execution.

Official references:
- https://learn.microsoft.com/en-us/azure/automation/enable-managed-identity-for-automation
- https://learn.microsoft.com/en-us/azure/automation/learn/powershell-runbook-managed-identity
- https://learn.microsoft.com/en-us/powershell/module/az.compute/stop-azvm
