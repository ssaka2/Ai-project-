#!/usr/bin/env python3
"""Read-only Azure inventory for the free Career Desk deployment."""
import argparse
import json
import shutil
import subprocess
import sys


def az(*args):
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "json"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode:
        # Do not include raw responses, account identifiers, or credentials in reports.
        raise RuntimeError(
            f"Azure read failed ({' '.join(args[:3])}). Check Cloud Shell sign-in, "
            "subscription selection, permissions, and network access."
        )
    return json.loads(result.stdout)


def normalize_region(value):
    return "".join(value.lower().split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", default="careerdesk-free-rg")
    parser.add_argument("--location", help="Explicit proposed Windows F1 region, such as eastus")
    args = parser.parse_args()
    if not shutil.which("az"):
        parser.exit(1, "Azure CLI is required. Run this script in Azure Cloud Shell (Bash).\n")

    account = az("account", "show")
    locations = az("appservice", "list-locations", "--sku", "F1")
    regions = sorted({normalize_region(row["name"]) for row in locations})
    report = {
        "readOnly": True,
        "subscriptionState": account.get("state"),
        "resourceGroup": args.resource_group,
        "windowsF1Regions": regions,
        "requestedLocation": args.location,
        "plans": [],
        "databases": [],
        "blockers": [],
        "limitations": [
            "Region availability does not guarantee subscription quota or SQL free-offer eligibility.",
            "This report does not audit charges for other resources or deploy the application.",
            "SMTP, HTTPS, migrations, persistent keys, and live acceptance checks are still required.",
        ],
    }
    blockers = report["blockers"]
    if account.get("state") != "Enabled":
        blockers.append("The selected subscription is not Enabled.")
    if not args.location or not args.location.strip():
        blockers.append("Select an explicit region and rerun with --location REGION; do not submit a blank location.")
    elif normalize_region(args.location) not in regions:
        blockers.append("The requested region is not listed for Windows F1. Select a returned region.")

    if not az("group", "exists", "--name", args.resource_group):
        blockers.append("The resource group does not exist in the selected subscription.")
    else:
        group = az("group", "show", "--name", args.resource_group)
        report["resourceGroupLocation"] = group.get("location")
        for plan in az("appservice", "plan", "list", "--resource-group", args.resource_group):
            sku = plan.get("sku") or {}
            report["plans"].append({"name": plan["name"], "location": plan.get("location"), "sku": sku.get("name")})
            if sku.get("name") != "F1":
                blockers.append(f"Plan {plan['name']} is not F1. Review it; this script will not change or delete it.")
        for server in az("sql", "server", "list", "--resource-group", args.resource_group):
            for db in az("sql", "db", "list", "--resource-group", args.resource_group, "--server", server["name"]):
                if db["name"].split("/")[-1] == "master":
                    continue
                report["databases"].append({
                    "name": db["name"], "server": server["name"],
                    "location": db.get("location"), "status": db.get("status"),
                    "useFreeLimit": db.get("useFreeLimit"),
                    "freeLimitExhaustionBehavior": db.get("freeLimitExhaustionBehavior"),
                })
                if db.get("useFreeLimit") is not True or db.get("freeLimitExhaustionBehavior") != "AutoPause":
                    blockers.append(f"Database {db['name']}: free allowance with AutoPause is not verified. Do not assume $0 billing.")
        if not report["databases"]:
            blockers.append("No application SQL database was found in this resource group.")
        if not report["plans"]:
            blockers.append("No App Service plan was found; the web app has not been verified.")
    print(json.dumps(report, indent=2))
    return 2 if blockers else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"Preflight could not complete: {error}", file=sys.stderr)
        sys.exit(1)
