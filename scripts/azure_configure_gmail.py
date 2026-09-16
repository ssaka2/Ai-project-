#!/usr/bin/env python3
"""Configure existing CareerDesk SMTP from Azure Cloud Shell; no paid resources.

Requires Azure CLI already signed in and a Google-generated app password.
Authenticates to Gmail without sending mail. Never prints credentials.
"""
import getpass
import json
import os
import re
import smtplib
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import warnings

GROUP = "careerdesk-free-rg"
APP = "ssaka2-careerdesk-30cc2b36"
URL = "https://" + APP + ".azurewebsites.net"


def azure(*args):
    try:
        result = subprocess.run(
            ["az", *args, "--only-show-errors"],
            capture_output=True, text=True, timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SystemExit("Azure CLI unavailable or timed out. Run this in Azure Cloud Shell.") from None
    if result.returncode:
        raise SystemExit("Azure command failed. Check the selected subscription and access to the web app. No credentials printed.")
    return result.stdout


def read_settings():
    return {item["name"]: item["value"] for item in json.loads(azure(
        "webapp", "config", "appsettings", "list", "-g", GROUP, "-n", APP, "-o", "json"
    ))}


def credentials():
    print("Create an app password at https://myaccount.google.com/apppasswords")
    print("Use its 16 characters, not your Google login password or verification code.")
    with open("/dev/tty") as terminal:
        for _ in range(3):
            print("Gmail address: ", end="", flush=True)
            sender = terminal.readline().strip().lower()
            if re.fullmatch(r"[a-z0-9.+_-]+@gmail\.com", sender):
                break
            print("Enter the full personal Gmail address ending in @gmail.com.")
        else:
            raise SystemExit("No settings changed. Gmail address was not valid.")
    for _ in range(3):
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = "".join(getpass.getpass("Google app password (hidden): ").split())
        if len(password) != 16:
            print("Expected 16 characters after removing spaces. Copy the complete generated app password.")
            continue
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=25) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(sender, password)
        except smtplib.SMTPAuthenticationError:
            print("Google rejected these credentials. Generate an app password for this same Gmail account.")
            continue
        except (OSError, smtplib.SMTPException):
            raise SystemExit("Could not complete Gmail TLS/authentication check. No settings changed. Retry later.") from None
        print("Gmail authentication verified. No email sent.")
        return sender, password
    raise SystemExit("No settings changed. A valid Google app password is required.")


def save_settings(settings):
    with tempfile.TemporaryDirectory(prefix="careerdesk-email-") as folder:
        path = os.path.join(folder, "settings.json")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(settings, output)
        azure("webapp", "config", "appsettings", "set", "-g", GROUP, "-n", APP,
              "--settings", "@" + path, "-o", "none")
    saved = read_settings()
    if any(saved.get(key) != value for key, value in settings.items()):
        raise SystemExit("Settings could not be verified. Do not assume setup completed.")
    print("EMAIL SETTINGS SAVED AND VERIFIED. Temporary credential file removed.")


def check_health():
    statuses = {}
    for attempt in range(8):
        for endpoint in ("/health/live", "/health/ready"):
            try:
                with urllib.request.urlopen(URL + endpoint, timeout=15) as response:
                    statuses[endpoint] = response.status
            except urllib.error.HTTPError as error:
                statuses[endpoint] = error.code
            except (OSError, urllib.error.URLError):
                statuses[endpoint] = "unreachable"
        print("Health: " + ", ".join(f"{key}={value}" for key, value in statuses.items()), flush=True)
        if all(value == 200 for value in statuses.values()):
            print("STARTUP AND DATABASE HEALTH PASSED: " + URL)
            print("Next: register and verify receipt of the confirmation email, then test sign-in.")
            return
        if attempt < 7:
            time.sleep(10)
    raise SystemExit("Email settings saved, but health checks have not passed. Share only the health status lines for diagnosis.")


def main():
    if not read_settings().get("ConnectionStrings__DefaultConnection"):
        raise SystemExit("Database connection setting is missing. Configure the database first.")
    sender, password = credentials()
    save_settings({
        "Email__Enabled": "true", "Email__Host": "smtp.gmail.com",
        "Email__Port": "587", "Email__Security": "StartTls",
        "Email__FromAddress": sender, "Email__Username": sender,
        "Email__Password": password, "Identity__RequireConfirmedAccount": "true",
    })
    print("Waiting for Azure to recycle the app...", flush=True)
    check_health()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError, getpass.GetPassWarning):
        raise SystemExit("Stopped. Credentials were not printed. Rerun to verify setup.") from None
    except Exception:
        raise SystemExit("Setup could not finish. No diagnostic values printed to protect credentials. Rerun in Azure Cloud Shell.") from None
