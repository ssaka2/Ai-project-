#!/usr/bin/env bash
# CI-only isolated integration test. Requires root, iproute2, WireGuard tools, curl, Python.
set -euo pipefail
: "${VPN_API_TOKEN:?Set VPN_API_TOKEN}"
api_base=${VPN_API_BASE:-http://127.0.0.1:8090}
server_ns="vpn-test-server-$$"
client_ns="vpn-test-client-$$"
test_dir=$(mktemp -d)
umask 077
cleanup() {
  ip netns del "$server_ns" 2>/dev/null || true
  ip netns del "$client_ns" 2>/dev/null || true
  rm -rf "$test_dir"
}
trap cleanup EXIT
wg genkey > "$test_dir/server.key"
wg pubkey < "$test_dir/server.key" > "$test_dir/server.pub"
wg genkey > "$test_dir/client.key"
wg pubkey < "$test_dir/client.key" > "$test_dir/client.pub"
python3 - "$test_dir" <<'PY'
import json, os, sys, urllib.request
from pathlib import Path
root = Path(sys.argv[1])
base = os.environ.get('VPN_API_BASE', 'http://127.0.0.1:8090')
request = urllib.request.Request(base + '/api/peers', data=json.dumps({'name':'CI tunnel client', 'public_key':root.joinpath('client.pub').read_text().strip()}).encode(), headers={'Authorization':'Bearer ' + os.environ['VPN_API_TOKEN'], 'Content-Type':'application/json'})
with urllib.request.urlopen(request, timeout=5) as response:
    assert response.status == 201
    peer = json.load(response)
root.joinpath('peer.json').write_text(json.dumps(peer))
root.joinpath('address').write_text(peer['address'])
root.joinpath('id').write_text(peer['id'])
PY
curl --fail --silent -H "Authorization: Bearer $VPN_API_TOKEN" "$api_base/api/wireguard/peers.conf" > "$test_dir/peers.conf"
{
  echo '[Interface]'
  echo "PrivateKey = $(cat "$test_dir/server.key")"
  echo 'ListenPort = 51820'
} > "$test_dir/server-base.conf"
cat "$test_dir/server-base.conf" "$test_dir/peers.conf" > "$test_dir/server.conf"
{
  echo '[Interface]'
  echo "PrivateKey = $(cat "$test_dir/client.key")"
  echo '[Peer]'
  echo "PublicKey = $(cat "$test_dir/server.pub")"
  echo 'Endpoint = 192.0.2.1:51820'
  echo 'AllowedIPs = 10.77.0.1/32'
} > "$test_dir/client.conf"
ip netns add "$server_ns"
ip netns add "$client_ns"
ip -n "$server_ns" link add transport0 type veth peer name transport1 netns "$client_ns"
ip -n "$server_ns" addr add 192.0.2.1/30 dev transport0
ip -n "$client_ns" addr add 192.0.2.2/30 dev transport1
ip -n "$server_ns" link set transport0 up
ip -n "$client_ns" link set transport1 up
for ns in "$server_ns" "$client_ns"; do
  ip -n "$ns" link set lo up
  ip -n "$ns" link add wg0 type wireguard
done
ip netns exec "$server_ns" wg setconf wg0 "$test_dir/server.conf"
ip netns exec "$client_ns" wg setconf wg0 "$test_dir/client.conf"
ip -n "$server_ns" address add 10.77.0.1/24 dev wg0
ip -n "$client_ns" address add "$(cat "$test_dir/address")" dev wg0
ip -n "$server_ns" link set wg0 up
ip -n "$client_ns" link set wg0 up
ip -n "$client_ns" route add 10.77.0.1/32 dev wg0
ip netns exec "$client_ns" ping -c 3 -W 2 10.77.0.1
printf 'PASS: actual WireGuard tunnel carries traffic\n'
curl --fail --silent -X DELETE -H "Authorization: Bearer $VPN_API_TOKEN" "$api_base/api/peers/$(cat "$test_dir/id")" > /dev/null
curl --fail --silent -H "Authorization: Bearer $VPN_API_TOKEN" "$api_base/api/wireguard/peers.conf" > "$test_dir/peers.conf"
cat "$test_dir/server-base.conf" "$test_dir/peers.conf" > "$test_dir/server.conf"
ip netns exec "$server_ns" wg setconf wg0 "$test_dir/server.conf"
if ip netns exec "$client_ns" ping -c 1 -W 2 10.77.0.1; then
  echo 'FAIL: revoked peer still reaches server' >&2
  exit 1
fi
printf 'PASS: applying revocation blocks the tunnel\n'
