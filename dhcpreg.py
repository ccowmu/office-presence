#!/usr/bin/env python3

####################
# ARP table parser to find active devices on the local network
# and pair them up with registered MAC addresses
#
# Originally: DHCP lease parser by James Jenkins (aka: themind)
# Ported to Python 3, switched to `ip neigh` ARP format
####################

import json
import sys


USERS_FILE = "data/registrations.config"


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
    """Parse `ip neigh show` output to find active devices.

    Line format:
        192.168.1.1 dev eth0 lladdr e6:21:32:29:ca:2a REACHABLE
        192.168.1.98 dev eth0 lladdr 96:31:2c:ca:51:72 STALE
        192.168.1.237 dev eth0 FAILED
    """
    ignore_macs = GetIgnoreMacs()
    active_users = []
    other_macs = []

    for line in fp.read().strip().splitlines():
        parts = line.split()
        if 'lladdr' not in parts:
            continue
        if parts[-1] == 'FAILED':
            continue
        try:
            mac = parts[parts.index('lladdr') + 1].lower()
        except (ValueError, IndexError):
            continue
        if mac in ignore_macs:
            continue
        user = LookupMac(mac)
        if user and user not in active_users:
            active_users.append(user)
        elif not user and mac not in other_macs:
            other_macs.append(mac)

    return (active_users, other_macs)


if __name__ == "__main__":
    with open("arp.txt") as f:
        print(GetActive(f))
