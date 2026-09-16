# Deployment runbook (synthetic)

Before deploying, run database migrations against a disposable database.
The readiness endpoint checks database connectivity.
Restart the application container and verify readiness again.
If a deployment fails, roll back the application image to the prior release.
Never roll back a database migration without a reviewed recovery plan.
