# Railway deployment

This configuration prepares the existing ASP.NET Core application for Railway.
It does not create a Railway project, database, SMTP account, volume, or live URL.

## Service configuration

Deploy ssaka2/Ai-project- from main with the repository root as the service root.
The committed railway.json selects the Dockerfile, runs /app/migrate before
startup, and checks /health/ready. Keep the Dockerfile's normal entrypoint.

Railway's [configuration reference](https://docs.railway.com/config-as-code/reference)
and [pre-deploy command guide](https://docs.railway.com/deployments/pre-deploy-command)
describe these settings. A migration failure must block the release.

Set these values in Railway's service variables, never in the repository:

| Variable | Required value |
| --- | --- |
| ASPNETCORE_ENVIRONMENT | Production |
| PORT | 8080 |
| ASPNETCORE_HTTP_PORTS | 8080 |
| ConnectionStrings__DefaultConnection | SQL Server connection string for the deployment environment |
| AllowedHosts | Public application hostname and the platform's health-check hostname, separated by semicolons |
| Identity__RequireConfirmedAccount | true |
| Email__Enabled | true |
| Email__Host | SMTP provider host |
| Email__Port | SMTP provider TLS port |
| Email__Security | StartTls or SslOnConnect |
| Email__FromAddress | Verified sender address |
| Email__Username / Email__Password | SMTP provider credentials, where required |
| DataProtection__KeyPath | /var/keys |
| AI__Enabled | false until live provider configuration and evaluation are complete |

The database must be SQL Server; a PostgreSQL URL is not compatible with this
application. Use a production-licensed SQL Server service, certificate validation,
and an appropriately scoped login. The bundled pre-deploy task needs schema
permissions. For least privilege, run that task separately with a migration
identity and remove preDeployCommand from this file; give the running app only
its runtime database permissions.

Provision persistent storage at /var/keys that is writable by the Docker image's
non-root app user. Verify ownership on the actual platform before deployment.
Do not mount the database inside the web container. Back up the SQL database and
persistent application keys.

Configure and verify the actual hosting proxy/HTTPS integration before opening
registration. Check that confirmation and recovery links use the public HTTPS
origin. Do not enable unrestricted forwarded-header trust to conceal a proxy
configuration problem. The local Compose development settings and Mailpit inbox
are not production settings.

## Live acceptance checks

1. The deployment build and migration task finish successfully.
2. /health/live and /health/ready return 200 over the public HTTPS domain.
3. Two synthetic accounts receive confirmation emails through the real provider.
4. Sign-in, password recovery, jobs, resumes, drafts, JSON export, and text downloads work.
5. Each account cannot access the other's records.
6. Restart the service and verify data and authentication keys persist.
7. Demonstrate a database restore in a nonproduction environment.
8. Validate allowed hosts, proxy handling, and email-link HTTPS origin.

An HTTP 503 from readiness means the application cannot reach SQL Server or
committed migrations are pending. SMTP configuration errors stop startup when
confirmed accounts are required. Resolve the underlying setting; do not remove
the readiness check or disable confirmation to make deployment appear successful.

Live deployment and these acceptance checks require access to the selected Railway
workspace and its database/SMTP settings. CI's Docker test is not evidence of a
successful Railway deployment.
