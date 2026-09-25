# Cloud VPN Management Web API

A runnable Python REST service for a small WireGuard server: register client public keys, allocate tunnel addresses, revoke peers, and export the server's `[Peer]` configuration. SQLite persists records; Docker Compose packages the service for a Linux cloud VM. No paid API or third-party Python package is required.

This project separates the management API from the VPN tunnel. API changes become effective on WireGuard only after an administrator applies the exported configuration. `/health` reports database readiness, not tunnel connectivity. No cloud resource is provisioned by this repository.

## Run locally

Python 3.11+:

```sh
cd portfolio/cloud-vpn-api
export VPN_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 vpn_api.py
```

The API listens on `127.0.0.1:8090`. Keep the token available in your API-client terminal. To run the packaged version instead, set the same token and run:

```sh
docker compose up --build -d --wait
curl --fail http://127.0.0.1:8090/health
```

The Compose service runs as a non-root user with a read-only root filesystem and a writable data volume. It does not have network administration privileges or access to WireGuard private keys. Stop it with `docker compose down`; do not add `-v` unless intentionally deleting stored peer records.

## API

All `/api/` routes require `Authorization: Bearer YOUR_TOKEN`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/health` | Database readiness; no token required |
| GET | `/api/peers` | List active and revoked peer records |
| POST | `/api/peers` | Create from `name` and `public_key`; returns assigned address |
| DELETE | `/api/peers/{id}` | Mark revoked; repeated revocation is idempotent |
| GET | `/api/wireguard/peers.conf` | Export active server peer blocks as plain text |

POST returns 201; invalid fields return 400; duplicate keys or address exhaustion return 409; oversized bodies return 413; incorrect content type returns 415. Requests are capped at 4 KiB. Server address `10.77.0.1` is reserved; clients receive `10.77.0.2/32` through `10.77.0.254/32`. Revoked keys and addresses remain reserved to avoid accidental reuse before a server configuration is applied.

Generate the client's keys on its own device using WireGuard tools:

```sh
umask 077
wg genkey > client.key
wg pubkey < client.key > client.pub
python3 -c 'import json; print(json.dumps({"name":"My laptop","public_key":open("client.pub").read().strip()}))' > peer.json
curl --fail-with-body -H "Authorization: Bearer $VPN_API_TOKEN" -H 'Content-Type: application/json' --data-binary @peer.json http://127.0.0.1:8090/api/peers
```

Keep the returned `id` and `address`. Never send `client.key` to the API. A 32-byte base64 shape check cannot establish ownership of a public key; only register public keys from devices you administer.

Export and revoke:

```sh
curl --fail -H "Authorization: Bearer $VPN_API_TOKEN" http://127.0.0.1:8090/api/wireguard/peers.conf -o peers.conf
# Replace PEER_ID with the id returned when registering:
curl --fail -X DELETE -H "Authorization: Bearer $VPN_API_TOKEN" http://127.0.0.1:8090/api/peers/PEER_ID
```

A revocation response includes `apply_required: true`. Export and apply again to disconnect the peer; the API does not claim the running VPN changed immediately.

## Cloud server setup

Use a Linux VM you administer with Docker Compose, WireGuard tools, and kernel WireGuard support. VM billing, DNS, and provider accounts are outside this project. The following creates a private route from a client to the server, not a full internet-exit VPN.

1. Clone this repository onto the VM, enter this project directory, generate a token, and run the Compose commands above. Keep the token in your server's secret-management mechanism; do not commit it. Keep TCP 8090 private. Manage remotely through `ssh -L 8090:127.0.0.1:8090 YOUR_USER@SERVER_IP`, then call the API through localhost. A public management endpoint additionally needs a hardened HTTPS reverse proxy and rate limiting.
2. Permit UDP 51820 in the cloud security group and host firewall for your client networks. Preserve your existing SSH access. The VPN service uses UDP; the HTTP API is a separate TCP service.
3. On a new server with no existing `wg0`, generate a server key with `wg genkey`, derive its public key using `wg pubkey`, and protect the private key with owner-only permissions. Create `/etc/wireguard/wg0.conf` as root with mode 600:

```ini
[Interface]
Address = 10.77.0.1/24
ListenPort = 51820
PrivateKey = REPLACE_WITH_SERVER_PRIVATE_KEY

# Append the exact active [Peer] blocks exported by the API here.
```

4. Register the client's public key with the API. Append the exported peer blocks to the server configuration, then run `sudo wg-quick up wg0`. Use `sudo wg show wg0` to inspect the interface. Optionally enable it after validation with `sudo systemctl enable wg-quick@wg0`.
5. On the client, import a local configuration with its returned address and the server's public key/IP:

```ini
[Interface]
PrivateKey = REPLACE_WITH_CLIENT_PRIVATE_KEY
Address = REPLACE_WITH_ASSIGNED_ADDRESS

[Peer]
PublicKey = REPLACE_WITH_SERVER_PUBLIC_KEY
Endpoint = SERVER_IP:51820
AllowedIPs = 10.77.0.1/32
PersistentKeepalive = 25
```

6. Connect and test `ping 10.77.0.1`. This route reaches only the server's VPN address; forwarding, client-to-client routing, NAT, and DNS changes are not enabled.
7. After additions or revocations, replace the complete peer-block section in the server file with a fresh API export, retaining the protected `[Interface]` section. Apply the desired peer set with `sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'`. Verify `sudo wg show wg0`; revoked public keys must no longer appear. Do not append repeated exports or use an old export after revocation.

See the [official WireGuard quick start](https://www.wireguard.com/quickstart/) for key generation, interface setup, and keepalive behavior. Do not print or commit private-key configurations.

## Verification

```sh
python3 -m unittest discover -s portfolio/cloud-vpn-api -v
```

Run that command from the repository root. The 10 tests exercise real HTTP requests against a temporary server/database, including unauthorized requests, validation, concurrent allocations, restart persistence, configuration export, and revocation.

CI also builds the Docker image, checks persistence across a container restart, and creates two disposable Linux network namespaces. `verify_tunnel.sh` registers an actual generated WireGuard public key through the API, applies the exported config, sends traffic through the tunnel, revokes the peer, reapplies the export, and checks that traffic is blocked. This needs root and Linux network namespace/WireGuard support; ordinary unit tests do not. The test creates isolated interfaces and removes them on exit.

## Limits

One shared administrator token, one fixed IPv4 pool, and one SQLite file; no user accounts, key rotation workflow, traffic accounting, billing, client app, or automatic host changes. The standard-library HTTP server is intended for a small private demonstration behind controlled access, not a public production edge. Put backups and access controls around the data volume, and test restore before relying on it. Revoked records are retained; rebuilding the pool requires coordinated server configuration and database maintenance. No production availability or public deployment is claimed.
