# office-presence

Tracks who is physically in the cclub office based on devices currently visible
on the morgana LAN (192.168.1.0/24). **Opt-in only** — MAC addresses must be
explicitly registered by the owner before they appear in output.

## Architecture

```
albatross (192.168.1.7)          yakko (141.218.143.78)
  cron: ip neigh show vmbr0  -->  /tmp/morgana-arp.txt
  (every minute, SSH push)            |
                                      v
                               office-presence container
                               (Docker, ccawmunity compose)
                                      |
                                      v
                               ccawmunity bot
                               ($office command)
```

albatross pushes its ARP table to yakko every minute using a
command-restricted SSH key. The key can only write `/tmp/morgana-arp.txt`
and nothing else.

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

The `arp.txt` file is bind-mounted from `/tmp/morgana-arp.txt` on the host.
If the file is missing the service returns empty results gracefully.

### albatross

**One-time setup** — generate a dedicated SSH key and authorize it on yakko:

```bash
ssh-keygen -t ed25519 -C "albatross-office-presence" \
    -f /root/.ssh/office_presence_key -N ""
```

Add the public key to `sysadmin@yakko:~/.ssh/authorized_keys` with a
command restriction:

```
command="cat > /tmp/morgana-arp.txt",restrict ssh-ed25519 <pubkey> albatross-office-presence
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

Install the push script at `/usr/local/bin/push-arp.sh`:

```bash
#!/bin/bash
ip neigh show dev vmbr0 | ssh -F /root/.ssh/config_office_presence yakko-office
```

Add to crontab:

```
* * * * * /usr/local/bin/push-arp.sh
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
