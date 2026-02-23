#!/usr/bin/env python3

# Contributors:
#     sphinx
#     themind (jpypi on Github)

import flask
import dhcpreg
import json
import os
import threading
import time
from re import compile as re_compile


app = flask.Flask(__name__)

FAIL = 'failure'
FAILURE = (FAIL, 400, [])

SESSIONS_FILE = "data/sessions.json"
POLL_INTERVAL = 5  # seconds between lease file polls

# {mac: arrival_timestamp} — updated by background thread
_sessions = {}
_sessions_lock = threading.Lock()


valid_mac_patt = re_compile("[:\-]".join(("[0-9a-fA-F]{2}",)*6))
def ValidateMac(mac_string):
    if valid_mac_patt.match(mac_string):
        return mac_string.replace("-", ":").lower()
    return False


def _load_sessions():
    try:
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def _save_sessions(sessions):
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    tmp = SESSIONS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sessions, f)
    os.replace(tmp, SESSIONS_FILE)


def _fmt_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return "%ds" % seconds
    minutes = seconds // 60
    if minutes < 60:
        return "%dm" % minutes
    hours = minutes // 60
    mins = minutes % 60
    if mins:
        return "%dh %dm" % (hours, mins)
    return "%dh" % hours


def _poll_leases():
    """Background thread: poll dhcp4.leases every POLL_INTERVAL seconds.

    Maintains _sessions: records arrival time when a MAC first appears,
    removes it when it disappears from active leases.
    """
    global _sessions
    with _sessions_lock:
        _sessions = _load_sessions()

    while True:
        try:
            with open("dhcp4.leases") as f:
                active_macs = dhcpreg.GetActiveMacs(f)
        except FileNotFoundError:
            active_macs = {}

        now = time.time()
        with _sessions_lock:
            # Add new arrivals
            for mac in active_macs:
                if mac not in _sessions:
                    # Prefer the lease start time from DHCP; fall back to now
                    lease_start = active_macs[mac]
                    _sessions[mac] = lease_start if lease_start else now

            # Remove departed MACs
            departed = [mac for mac in _sessions if mac not in active_macs]
            for mac in departed:
                del _sessions[mac]

            if departed or set(active_macs) - set(_sessions):
                _save_sessions(dict(_sessions))

        time.sleep(POLL_INTERVAL)


def _get_presence():
    """Return (registered, others) where registered is a list of
    (nick, arrival_ts) tuples sorted by arrival time, and others is a count."""
    with _sessions_lock:
        sessions = dict(_sessions)

    registered = {}  # nick -> earliest arrival
    others = 0
    for mac, arrival in sessions.items():
        nick = dhcpreg.LookupMac(mac)
        if nick:
            if nick not in registered or (arrival and arrival < registered[nick]):
                registered[nick] = arrival
        else:
            others += 1

    ordered = sorted(registered.items(), key=lambda x: (x[1] is None, x[1]))
    return ordered, others


@app.route('/reg', methods=['POST'])
def reg():
    mac_addr = ValidateMac(flask.request.form.get('mac', ''))
    nick = flask.request.form.get('nick', '')
    if mac_addr and nick:
        if dhcpreg.RegisterMac(mac_addr, nick):
            return 'success'
    return FAILURE


@app.route('/dereg', methods=['POST'])
def dereg():
    mac_addr = ValidateMac(flask.request.form.get('mac', ''))
    nick = flask.request.form.get('nick', '')
    if mac_addr and nick and dhcpreg.DeregisterMac(mac_addr, nick):
        return 'success'
    return FAIL


@app.route('/list', methods=['POST'])
def list_nick_macs():
    nick = flask.request.form.get('nick', '')
    if nick:
        mac_addresses = dhcpreg.LookupNick(nick)
        if mac_addresses:
            return flask.json.dumps(mac_addresses)
    return FAILURE


@app.route('/json')
def json_resp():
    registered, others = _get_presence()
    now = time.time()
    result = []
    for nick, arrival in registered:
        entry = {"nick": nick}
        if arrival:
            entry["arrived"] = int(arrival)
            entry["duration"] = _fmt_duration(now - arrival)
        result.append(entry)
    return flask.json.dumps({"registered": result, "others": others})


@app.route('/plain')
def plain_resp():
    registered, others = _get_presence()
    now = time.time()
    parts = []
    for nick, arrival in registered:
        if arrival:
            parts.append("%s (%s)" % (nick, _fmt_duration(now - arrival)))
        else:
            parts.append(nick)
    extra = ""
    if others > 0:
        extra = " - Unregistered: %d" % others
    return ", ".join(parts) + extra


if __name__ == '__main__':
    t = threading.Thread(target=_poll_leases, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5001)
