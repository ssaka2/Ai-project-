# Alternative test shutdown safeguard

## Recorded setup and remaining verification

Observed October 10, 2026: the approved `ai-office-shutdown` Automation account
was created in **West US**, with a system-assigned managed identity and the
`AI Office VM Deallocator` custom role assigned at the exact target VM resource.
The `Stop-OfficeVm` PowerShell runbook was published. Its test job completed with
`VM already deallocated.` This verified the read/idempotent path, not shutdown of
a running VM. No one-time shutdown schedule was created during that setup.

The VM was independently observed as stopped/deallocated on October 11, 2026.
These are dated observations, not a live status query. Read back the resources,
identity, role scope, runbook and VM state before any future pilot. Reuse the
existing approved resources if they still match; do not recreate them blindly.
A new enabled one-time schedule with verified parameters is still required
before starting the VM.

The built-in shutdown scheduler rejected Mexico Central as unsupported. A schedule
in Central US was also rejected because it must be colocated with its target VM.
Azure Automation is a separate service and runs its runbook against Azure Resource
Manager; the runbook does not need to run on the target VM.

## Approved access scope

The observed Automation deployment is in West US. Central US was part of the
initial proposal and is not the installed account location. For this installation,
verify the existing system-assigned identity and `AI Office VM Deallocator` role
against `stop-vm-role.template.json`. Its assignment must remain **at the exact
resource ID of ssaka2-portfolio-vm**, never at subscription or resource-group
scope. The assignable scope in the definition is where the role may be assigned;
it is not a role assignment and grants no permissions itself.

The three allowed operations read VM metadata/power state and deallocate it.
There are no candidate-data, mailbox, secret-store, VM command execution, VM
creation, restart, resize, deletion, or role-administration permissions.

The existing identity and narrow assignment were explicitly approved during
setup. That approval does not authorize broader permissions or a replacement
identity. Verify account usage and costs before a pilot; do not promise hosting
is unconditionally free.

## Installation and acceptance gates

1. Read back the existing West US Automation account and identity; do not start
   the VM yet. Resolve any missing or unexpected configuration before launch.
2. Verify compatible Az.Accounts and Az.Compute modules in its PowerShell runtime
   and confirm the published `Stop-OfficeVm.ps1` content.
3. Verify the approved role assignment remains at the one VM resource ID. Never
   expand the role to fix a permission or propagation error.
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
automatic applications, mailbox OAuth, or verified live-model execution.

Official references:
- https://learn.microsoft.com/en-us/azure/automation/enable-managed-identity-for-automation
- https://learn.microsoft.com/en-us/azure/automation/learn/powershell-runbook-managed-identity
- https://learn.microsoft.com/en-us/powershell/module/az.compute/stop-azvm
