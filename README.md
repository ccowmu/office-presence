# office-presence

Tracks who is physically in the cclub office based on active DHCP leases
on the morgana LAN (192.168.1.0/24). **Opt-in only** — MAC addresses must be
explicitly registered by the owner before they appear in output.

## Architecture

```
condor/pfSense (192.168.1.1)       yakko (141.218.143.78)
  cron: cat /var/dhcpd/.../         /tmp/morgana-dhcp.leases
        dhcpd.leases            -->       |
  (every minute, SSH push)               v
                                  office-presence container
                                  (Docker, ccawmunity compose)
                                          |
                                          v
                                  ccawmunity bot
                                  ($office command)
```

condor pushes its DHCP leases file to yakko every minute using a
command-restricted SSH key. The key can only write `/tmp/morgana-dhcp.leases`
and nothing else.

Using DHCP leases (rather than ARP) means presence data is authoritative:
devices appear when they get a lease and disappear when it expires.

## Privacy

This service is **opt-in**. Unregistered devices appear only as a count
("Unregistered: N"). A device only maps to a name after the owner explicitly
runs `$office -r <mac>`.

## Deployment

### yakko

The service runs as `office-presence` in ccawmunity's `docker-compose.yml`.
Registrations persist in a named Docker volume (`ccawmunity_office-data`).

```bash
cd /home/sysadmin/ccawmunity
docker compose up -d
```

The `dhcpd.leases` file is bind-mounted from `/tmp/morgana-dhcp.leases` on
the host. If the file is missing the service returns empty results gracefully.

### condor (pfSense)

**One-time setup** — generate a dedicated SSH key and authorize it on yakko:

```bash
ssh-keygen -t ed25519 -C "condor-office-presence" \
    -f /root/.ssh/office_presence_key -N ""
```

Add the public key to `sysadmin@yakko:~/.ssh/authorized_keys` with a
command restriction:

```
command="cat > /tmp/morgana-dhcp.leases",restrict ssh-ed25519 <pubkey> condor-office-presence
```

Create `/root/.ssh/config_office_presence`:

```
Host yakko-office
    HostName 141.218.143.78
    User sysadmin
    IdentityFile /root/.ssh/office_presence_key
    IdentitiesOnly yes
    StrictHostKeyChecking yes
```

Pre-accept yakko's host key:

```bash
ssh-keyscan -H 141.218.143.78 >> /root/.ssh/known_hosts
```

Install the push script at `/usr/local/bin/push-dhcp.sh`:

```sh
#!/bin/sh
cat /var/dhcpd/var/db/dhcpd.leases | ssh -F /root/.ssh/config_office_presence yakko-office
```

Add to `/usr/local/etc/cron.d/office-presence`:

```
* * * * * root /usr/local/bin/push-dhcp.sh
```

## API

| Method | Path    | Params       | Returns |
|--------|---------|--------------|---------|
| GET    | /plain  |              | `nick1, nick2 - Unregistered: N` |
| GET    | /json   |              | `{"registered": [...], "others": N}` |
| POST   | /reg    | nick, mac    | `success` or `failure` |
| POST   | /dereg  | nick, mac    | `success` or `failure` |
| POST   | /list   | nick         | `["mac1", "mac2"]` or `failure` |

## Configuration

**`ignorelist.config`** (optional) — one MAC per line, lines starting with
`#` are comments. MACs listed here are excluded from all output including
the unregistered count. Use this for permanent fixtures (servers, APs, etc.).

```
# office AP
aa:bb:cc:dd:ee:ff
# desktop in the corner
11:22:33:44:55:66
```

**`data/registrations.config`** — auto-managed JSON file mapping MAC
addresses to nicks. Do not edit by hand while the service is running.
