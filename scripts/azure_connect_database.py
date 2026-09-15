#!/usr/bin/env python3
"""Configure an existing free Azure deployment. Run in the authenticated Cloud Shell.

Creates a dedicated contained SQL user with data-reader/writer roles, tests it,
and saves only its connection in App Service. Requires the existing build folder.
Does not configure SMTP or claim a healthy deployment. Re-running creates a new
user; it does not remove existing users or rotate their passwords.
"""
import argparse
import getpass
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import urllib.request
import uuid


CSHARP = r'''
using Microsoft.Data.SqlClient;

try
{
    var user = Environment.GetEnvironmentVariable("CAREERDESK_RUNTIME_USER")!;
    var password = Environment.GetEnvironmentVariable("CAREERDESK_RUNTIME_PASSWORD")!;
    var builder = new SqlConnectionStringBuilder {
        DataSource = Environment.GetEnvironmentVariable("CAREERDESK_SQL_HOST"),
        InitialCatalog = "careerdesk", UserID = "careerdeskadmin",
        Password = Environment.GetEnvironmentVariable("CAREERDESK_ADMIN_PASSWORD"),
        TrustServerCertificate = false, ConnectTimeout = 60
    };
    builder["Encrypt"] = "True";
    using (var admin = new SqlConnection(builder.ConnectionString))
    {
        await admin.OpenAsync();
        using var transaction = admin.BeginTransaction();
        using var command = admin.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            DECLARE @statement nvarchar(max) =
                N'CREATE USER ' + QUOTENAME(@username) + N' WITH PASSWORD = ' + QUOTENAME(@password, NCHAR(39)) + N';' +
                N'ALTER ROLE db_datareader ADD MEMBER ' + QUOTENAME(@username) + N';' +
                N'ALTER ROLE db_datawriter ADD MEMBER ' + QUOTENAME(@username) + N';';
            EXEC sp_executesql @statement;
            """;
        command.Parameters.AddWithValue("@username", user);
        command.Parameters.AddWithValue("@password", password);
        await command.ExecuteNonQueryAsync();
        transaction.Commit();
    }
    builder.UserID = user;
    builder.Password = password;
    using var runtime = new SqlConnection(builder.ConnectionString);
    await runtime.OpenAsync();
    using var verify = runtime.CreateCommand();
    verify.CommandText = "SELECT COUNT(*) FROM dbo.__EFMigrationsHistory";
    if (Convert.ToInt32(await verify.ExecuteScalarAsync()) < 3)
        throw new InvalidOperationException();
    Console.WriteLine("Dedicated database user created and connection verified.");
    return 0;
}
catch (SqlException error)
{
    Console.Error.WriteLine($"SQL setup failed (SQL error {error.Number}). No credentials are printed.");
    return 1;
}
catch
{
    Console.Error.WriteLine("SQL setup or migration verification failed. No credentials are printed.");
    return 1;
}
'''


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode:
        # A CLI error can contain configuration values; do not echo its raw output.
        raise RuntimeError(f"Step failed: {' '.join(command[:3])}. Settings may be incomplete; no secrets printed.")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", required=True)
    args = parser.parse_args()
    build = Path(args.build_dir).resolve()
    assets = build / "source/src/AiCareerDesk.Web/obj/project.assets.json"
    if not assets.is_file() or not (build / "dotnet/dotnet").is_file():
        raise RuntimeError("Build files are missing. Rebuild in this Cloud Shell session first.")
    libraries = json.loads(assets.read_text())["libraries"]
    version = next(key.split("/", 1)[1] for key in libraries if key.startswith("Microsoft.Data.SqlClient/"))
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(build / "dotnet")
    env["PATH"] = env["DOTNET_ROOT"] + os.pathsep + env["PATH"]
    group = "careerdesk-free-rg"
    app = "ssaka2-careerdesk-30cc2b36"
    server = "ssaka2-careerdesk-sql-30cc2b36"
    plan = json.loads(run(["az", "appservice", "plan", "show", "-g", group, "-n", "careerdesk-free-plan", "-o", "json"]))
    db = json.loads(run(["az", "sql", "db", "show", "-g", group, "-s", server, "-n", "careerdesk", "-o", "json"]))
    web = json.loads(run(["az", "webapp", "show", "-g", group, "-n", app, "-o", "json"]))
    if plan["sku"]["name"] != "F1" or not web["serverFarmId"].lower() == plan["id"].lower():
        raise RuntimeError("The app is not verified on the intended F1 plan. No settings changed.")
    if db.get("useFreeLimit") is not True or db.get("freeLimitExhaustionBehavior") != "AutoPause":
        raise RuntimeError("SQL free allowance with AutoPause is not verified. No settings changed.")
    if not web.get("httpsOnly"):
        raise RuntimeError("HTTPS-only is not enabled. No settings changed.")

    with tempfile.TemporaryDirectory(prefix="careerdesk-connect-") as directory:
        root = Path(directory)
        (root / "Setup.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            '<TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
            '</PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Data.SqlClient" Version="'
            + version + '" /></ItemGroup></Project>')
        (root / "Program.cs").write_text(CSHARP)
        print("Building database setup utility...", flush=True)
        run(["dotnet", "build", "-c", "Release"], cwd=root, env=env)
        env["CAREERDESK_ADMIN_PASSWORD"] = getpass.getpass("Existing SQL admin password: ")
        env["CAREERDESK_RUNTIME_USER"] = "careerdesk_app_" + uuid.uuid4().hex[:12]
        env["CAREERDESK_RUNTIME_PASSWORD"] = secrets.token_hex(24) + "Aa1!"
        env["CAREERDESK_SQL_HOST"] = f"tcp:{server}.database.windows.net,1433"
        with urllib.request.urlopen("https://api.ipify.org", timeout=20) as response:
            address = str(ipaddress.IPv4Address(response.read().decode().strip()))
        rule = "careerdesk-connect-" + uuid.uuid4().hex[:12]
        target = ["-g", group, "-s", server, "-n", rule]
        run(["az", "sql", "server", "firewall-rule", "create", *target,
             "--start-ip-address", address, "--end-ip-address", address, "-o", "none"])
        try:
            print("Creating and verifying the dedicated database user...", flush=True)
            result = subprocess.run(["dotnet", str(root / "bin/Release/net10.0/Setup.dll")],
                                    env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "Database user setup failed.")
            connection = (f'Server={env["CAREERDESK_SQL_HOST"]};Database=careerdesk;'
                          f'User ID={env["CAREERDESK_RUNTIME_USER"]};Password={env["CAREERDESK_RUNTIME_PASSWORD"]};'
                          'Encrypt=True;TrustServerCertificate=False;Connection Timeout=60;')
            settings = {
                "ConnectionStrings__DefaultConnection": connection,
                "ASPNETCORE_ENVIRONMENT": "Production",
                "AllowedHosts": web["defaultHostName"],
                "AI__Enabled": "false",
                "Identity__RequireConfirmedAccount": "true",
            }
            settings_file = root / "settings.json"
            with settings_file.open("x") as output:
                os.chmod(settings_file, 0o600)
                json.dump(settings, output)
            print("Saving connection settings in Azure...", flush=True)
            run(["az", "webapp", "config", "appsettings", "set", "-g", group, "-n", app,
                 "--settings", "@" + str(settings_file), "-o", "none"])
        finally:
            try:
                run(["az", "sql", "server", "firewall-rule", "delete", *target])
            except RuntimeError:
                raise RuntimeError(f"Remove temporary SQL firewall rule {rule} in the Azure portal; cleanup failed.")
    print("DATABASE CONNECTION CONFIGURED. Temporary firewall rule and local secret file removed.")
    print("SMTP setup and live health checks are still required. Settings changes may recycle the app.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as error:
        raise SystemExit(str(error))
