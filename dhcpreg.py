#!/usr/bin/env python3

####################
# DHCP lease parser to find leases that haven't expired
# and pair them up with registered MAC addresses
#
# Contributors:
#     James Jenkins (aka: themind)
####################

import re
import datetime
import json
import sys
import time


USERS_FILE = "data/registrations.config"

mac_patt        = re.compile("hardware ethernet ([0-9A-Fa-f:]+?);")
lease_patt      = re.compile(r"lease ([0-9\.]+?) {(.+?)}", re.DOTALL)
end_time_patt   = re.compile(r"ends (?:[0-9] ([0-9:/ ]+?);|(never))")


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


def GetActive(fp):
    """Parse a dhcpd.leases file and return active leases matched to nicks."""
    data = fp.read()
    now = datetime.datetime.utcnow()
    ignore_macs = GetIgnoreMacs()
    active_users = []
    other_macs = []

    for lease in lease_patt.findall(data):
        match = end_time_patt.search(lease[1])
        if not match:
            continue
        end_time_s = match.group(1)
        end_time = None
        if end_time_s and end_time_s != "never":
            end_time = datetime.datetime.strptime(end_time_s, "%Y/%m/%d %H:%M:%S")

        if end_time is not None and now >= end_time:
            continue

        macs = mac_patt.findall(lease[1])
        if not macs:
            continue
        mac = macs[0].lower()

        if mac in ignore_macs:
            continue

        user = LookupMac(mac)
        if user and user not in active_users:
            active_users.append(user)
        elif not user and mac not in other_macs:
            other_macs.append(mac)

    return (active_users, other_macs)


if __name__ == "__main__":
    with open("dhcpd.leases") as f:
        print(GetActive(f))
