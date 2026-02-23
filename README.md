# office-presence

Tracks who is physically in the cclub office based on active DHCP leases
on the morgana LAN (192.168.1.0/24). **Opt-in only** — MAC addresses must be
explicitly registered by the owner before they appear in output.

## Architecture

```
condor/pfSense (192.168.1.1)       yakko (141.218.143.78)
  daemon: push-dhcp.sh              /tmp/morgana-dhcp.leases
  (every ~10 seconds, SSH push) -->        |
                                           v
                                   office-presence container
                                   (Docker, ccawmunity compose)
                                   - polls leases every 5s
                                   - tracks session arrival times
                                           |
                                           v
                                   ccawmunity bot
                                   ($office command)
```

condor pushes its DHCP leases file to yakko every ~10 seconds using a
command-restricted SSH key. The key can only write `/tmp/morgana-dhcp.leases`
and nothing else.

The container polls the leases file every 5 seconds and maintains session
state in `data/sessions.json`. Arrivals are recorded when a MAC first appears;
departures are detected when the lease is released or expires.

Uses Kea DHCP4 memfile CSV format (pfSense 2.8+). A lease is active when
`state == 0` (STATE_DEFAULT) and its expiry timestamp is in the future.
Departure is detected when a lease transitions out of state 0 or expires.

## Privacy

This service is **opt-in**. Unregistered devices appear only as a count
("Unregistered: N"). A device only maps to a name after the owner explicitly
runs `$office -r <mac>`.

## Deployment

### yakko

The service runs as `office-presence` in ccawmunity's `docker-compose.yml`.
Registrations and session state persist in a named Docker volume
(`ccawmunity_office-data`).

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
cat /var/lib/kea/dhcp4.leases | ssh -F /root/.ssh/config_office_presence yakko-office
```

> **Note:** pfSense 2.8+ uses Kea DHCP instead of ISC dhcpd. The lease file
> moved from `/var/dhcpd/var/db/dhcpd.leases` to `/var/lib/kea/dhcp4.leases`
> and uses CSV format instead of the old ISC config syntax.

Make it executable:

```bash
chmod 700 /usr/local/bin/push-dhcp.sh
```

**Replace the 1-minute cron with a persistent 10-second daemon.**

Install the rc.d script at `/usr/local/etc/rc.d/office_presence`:

```sh
#!/bin/sh
#
# PROVIDE: office_presence
# REQUIRE: LOGIN
# KEYWORD: shutdown

. /etc/rc.subr

name="office_presence"
rcvar="${name}_enable"
command="/usr/local/bin/push-dhcp-loop.sh"
pidfile="/var/run/${name}.pid"
start_cmd="${name}_start"
stop_cmd="${name}_stop"

office_presence_start() {
    /usr/sbin/daemon -p "$pidfile" -r "$command"
    echo "office_presence started"
}

office_presence_stop() {
    if [ -f "$pidfile" ]; then
        kill "$(cat "$pidfile")"
        rm -f "$pidfile"
    fi
    echo "office_presence stopped"
}

load_rc_config "$name"
: "${office_presence_enable:=NO}"
run_rc_command "$1"
```

Install the loop script at `/usr/local/bin/push-dhcp-loop.sh`:

```sh
#!/bin/sh
while true; do
    /usr/local/bin/push-dhcp.sh 2>/dev/null
    sleep 10
done
```

Make both executable:

```bash
chmod 700 /usr/local/bin/push-dhcp-loop.sh
chmod 755 /usr/local/etc/rc.d/office_presence
```

Enable and start:

```
# In /etc/rc.conf.local (or pfSense System > Advanced > rc.conf):
office_presence_enable="YES"
```

```bash
service office_presence start
```

Remove the old cron entry from `/usr/local/etc/cron.d/office-presence` if it exists.

## API

| Method | Path    | Params       | Returns |
|--------|---------|--------------|---------|
| GET    | /plain  |              | `nick1 (2h 15m), nick2 (45m) - Unregistered: N` |
| GET    | /json   |              | `{"registered": [{"nick": "...", "arrived": ts, "duration": "2h 15m"}], "others": N}` |
| POST   | /reg    | nick, mac    | `success` or `failure` |
| POST   | /dereg  | nick, mac    | `success` or `failure` |
| POST   | /list   | nick         | `["mac1", "mac2"]` or `failure` |

Duration strings: `30s`, `45m`, `2h`, `2h 15m`

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

**`data/sessions.json`** — auto-managed JSON file recording current session
arrival timestamps per MAC. Cleared when MACs depart. Do not edit by hand
while the service is running.
