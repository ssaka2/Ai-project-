"""Create local development secrets without replacing an existing environment file."""
from pathlib import Path
import os
import secrets

target = Path(__file__).resolve().parent.parent / ".env"
if target.exists():
    print("Existing .env kept. Run docker compose up --build -d.")
else:
    password = secrets.token_hex(24) + "Aa1!"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("SQL_PASSWORD=" + password + "\nAI_ENABLED=false\nAI_MODEL=\nAI_API_KEY=\n")
    print("Local configuration created. Run docker compose up --build -d.")
