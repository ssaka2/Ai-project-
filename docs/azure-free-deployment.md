# Azure free deployment: diagnose before provisioning

The deployment target is Windows App Service F1 and the Azure SQL free offer.
No Azure deployment has been verified. The repository's Docker/SQL/browser CI
success does not establish that the Azure resources exist or that the app is live.

## Get a useful diagnostic report

Run in Azure Cloud Shell **Bash** with the intended subscription selected:

```bash
git clone --branch codex/azure-free-preflight https://github.com/ssaka2/Ai-project-.git careerdesk-azure-check
cd careerdesk-azure-check
python3 scripts/azure_preflight.py
```

The script only reads Azure metadata. It never creates, modifies, or deletes
resources, registers providers, lists app secrets, or prints connection strings.
It reports Windows F1 regions, plans and databases in `careerdesk-free-rg`,
and whether each database advertises the free allowance with `AutoPause`.
Use `--resource-group YOUR_GROUP` if the resources are elsewhere.

Choose a returned region, then rerun with an explicit location:

```bash
python3 scripts/azure_preflight.py --location YOUR_REGION
```

Exit code 2 means blockers were found, including missing resources; 1 means a
read failed; 0 means the reported checks passed, not that deployment is complete.
Share the JSON report to diagnose the next step. Region listings do not prove
that a subscription has provisioning quota. This does not audit other resources
or promise that the entire Azure account has no charges.

## Resolve LocationRequired

This error says a submitted definition lacks a location; it does not identify
the resource or mean that application code failed. Preserve the exact failing
command or the deployment operation details (without secrets).

When using the portal, explicitly select a server and its region on the SQL
creation form. With CLI or templates, provide the location on the resource
definition that failed, using a region verified for that service. A resource
group's location does not automatically fill every resource's location.
The preflight script itself does not submit resource definitions.

## Preserve the zero-charge constraint

- Select **F1 Free** for the Windows web app. Do not accept a paid replacement
  when quota or regional capacity is unavailable.
- Start SQL creation from the [Azure SQL hub](https://aka.ms/azuresqlhub) using
  **Start free**. Require the free-offer banner and zero estimated cost.
- Keep **Auto-pause the database until next month** selected. Never select
  **Continue using database for additional charges**.
- Leave paid AI calls disabled. Confirm a suitable free SMTP arrangement before
  opening registration; do not disable account confirmation to hide missing SMTP.
- Use the included web hostname. Do not add paid monitoring, private endpoints,
  custom-domain purchases, or other optional resources.

The SQL free offer has quotas and may pause the database. Students Starter is
not eligible for this SQL offer. Consult Microsoft's
[SQL free-offer requirements](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-offer)
and [F1 pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/windows/).

After resources are verified, deployment still needs a Windows-compatible .NET
publish, production SQL/SMTP settings, migrations, persistent Data Protection
keys, and public HTTPS checks for login, recovery, private records, and exports.
The Linux Docker migration binary is not a Windows deployment artifact.
