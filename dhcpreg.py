#!/usr/bin/env python3

####################
# DHCP lease parser to find active leases and pair them with registered nicks.
#
# Contributors:
#     James Jenkins (aka: themind)
####################

import re
import datetime
import json
import sys


USERS_FILE = "data/registrations.config"

mac_patt      = re.compile(r"hardware ethernet ([0-9A-Fa-f:]+?);")
lease_patt    = re.compile(r"lease ([0-9\.]+?) \{(.+?)\}", re.DOTALL)
end_time_patt = re.compile(r"ends (?:[0-9] ([0-9:/ ]+?);|(never))")
state_patt    = re.compile(r"binding state (\w+);")
start_patt    = re.compile(r"starts [0-9] ([0-9:/ ]+?);")


def LoadRegistrations():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def _save(users):
    import os
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def GetIgnoreMacs():
    try:
        with open("ignorelist.config", "r") as f:
            return [line.strip() for line in f
                    if line.strip() and not line.lstrip().startswith("#")]
    except IOError:
        sys.stderr.write("No ignorelist.config file\n")
    return []


def RegisterMac(mac, name):
    users = LoadRegistrations()
    if not users.get(mac.lower()):
        users[mac.lower()] = name
        _save(users)
        return True
    return False


def DeregisterMac(mac, nick):
    try:
        users = LoadRegistrations()
        if users[mac] == nick:
            del users[mac]
            _save(users)
            return True
    except (IOError, ValueError, KeyError):
        pass
    return False


def LookupMac(mac):
    try:
        return LoadRegistrations()[mac.lower()]
    except KeyError:
        return None


def LookupNick(nick):
    return [mac for mac, n in LoadRegistrations().items() if n == nick]


def GetActiveMacs(fp):
    """Return a dict of {mac: lease_start_timestamp} for all active leases.

    A lease is active if:
      - binding state is 'active', AND
      - end time is in the future (or 'never')
    """
    data = fp.read()
    now = datetime.datetime.utcnow()
    ignore_macs = GetIgnoreMacs()
    result = {}

    for lease in lease_patt.findall(data):
        body = lease[1]

        state_m = state_patt.search(body)
        if not state_m or state_m.group(1) != "active":
            continue

        end_m = end_time_patt.search(body)
        if not end_m:
            continue
        end_s = end_m.group(1)
        if end_s and end_s != "never":
            end_time = datetime.datetime.strptime(end_s, "%Y/%m/%d %H:%M:%S")
            if now >= end_time:
                continue

        macs = mac_patt.findall(body)
        if not macs:
            continue
        mac = macs[0].lower()

        if mac in ignore_macs:
            continue

        start_m = start_patt.search(body)
        if start_m:
            try:
                lease_start = datetime.datetime.strptime(
                    start_m.group(1), "%Y/%m/%d %H:%M:%S"
                ).timestamp()
            except ValueError:
                lease_start = None
        else:
            lease_start = None

        # Keep earliest start if the same MAC appears multiple times
        if mac not in result or (lease_start and lease_start < result[mac]):
            result[mac] = lease_start

    return result


def GetActive(fp):
    """Return (registered_nicks, other_macs) for all active leases."""
    active = GetActiveMacs(fp)
    active_users = []
    other_macs = []

    for mac in active:
        user = LookupMac(mac)
        if user and user not in active_users:
            active_users.append(user)
        elif not user and mac not in other_macs:
            other_macs.append(mac)

    return (active_users, other_macs)


if __name__ == "__main__":
    with open("dhcpd.leases") as f:
        print(GetActive(f))
