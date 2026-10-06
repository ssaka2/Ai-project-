# Private Azure/Linux pilot

This package keeps the office on localhost and runs discovery while the service is up. It is for a trusted operator using SSH, not a public candidate portal. It does not provision a VM, open Azure firewall ports, install an AI model or submit applications. Use synthetic candidate data until live integrations and access controls are verified. Hosting and local inference may consume credits/resources.

## Fresh Linux VM setup

Requires systemd, `/usr/bin/python3` version 3.11+, and an existing SSH account. Copy the repository's `portfolio/ai-office` directory to the VM and run these commands from that directory. These commands are for a fresh installation; do not overwrite a running deployment.

```sh
/usr/bin/python3 --version
sudo useradd --system --user-group --home-dir /var/lib/ai-office --shell /usr/sbin/nologin ai-office
sudo install -d -m 0755 /opt/ai-office
sudo install -m 0644 office.py recruiting.py lever_source.py ai_staff.py application_learning.py staff_chat.py app.js workflow.js index.html style.css verify_pilot.py /opt/ai-office/
sudo install -m 0600 deploy/ai-office.env.example /etc/ai-office.env
sudo install -m 0644 deploy/ai-office.service /etc/systemd/system/ai-office.service
sudo systemctl daemon-reload
sudo systemctl enable --now ai-office
sudo systemctl status ai-office --no-pager
```

The service user owns the private database directory created by systemd. Code remains root-owned and read-only to the service. Install and run Ollama separately on the same VM if model drafts are required. Set `AI_OFFICE_MODEL` in `/etc/ai-office.env` to an installed model name using `sudoedit`, then restart `ai-office`. The package does not choose hardware or automatically download models.

## Private access

From your computer, replace `YOUR_SSH_USER` and `YOUR_VM_ADDRESS` with the actual deployment details:

```sh
ssh -N -L 4521:127.0.0.1:4521 YOUR_SSH_USER@YOUR_VM_ADDRESS
```

Open `http://127.0.0.1:4521` on that computer. Keep ports 4521 and 11434 closed to public traffic. Do not change the app's localhost binding: candidate login and per-user access isolation are not implemented. The SSH account controls operator access.

## Verify before adding real candidate data

On the VM, first run:

```sh
python3 /opt/ai-office/verify_pilot.py
```

Exit 2 means incomplete or blocked checks, not success. To test live feeds and one synthetic inference, supply real employer board tokens:

```sh
python3 /opt/ai-office/verify_pilot.py --test-model --board YOUR_GREENHOUSE_TOKEN --board lever:YOUR_LEVER_TOKEN
```

The report prints statuses and counts, never CV text, tokens or generated text. It reads the local state API for its session token but does not modify records. Inference uses only fixed fictional input; no candidate profile is sent to the model. Feed checks do not write campaigns or mark openings as new. Exit 0 verifies connectivity only: it does not certify AI accuracy, autonomy, submissions, status tracking or placement.

For restart persistence, create a fictional candidate in the UI, restart with `sudo systemctl restart ai-office`, reconnect and verify that record remains. For ongoing operation, inspect `journalctl -u ai-office` and campaign last-scan/error fields. SQLite persists across restarts but an off-VM backup and a tested restore procedure are still required before real candidate use. The provided unit has not been exercised on your Azure VM until that deployment is available.
