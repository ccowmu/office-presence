#!/usr/bin/env python3

####################
# DHCP lease parser to find active leases and pair them with registered nicks.
#
# Parses Kea DHCP4 memfile CSV format (pfSense 2.8+).
# CSV columns: address,hwaddr,client_id,valid_lifetime,expire,subnet_id,
#              fqdn_fwd,fqdn_rev,hostname,state,user_context,pool_id
#
# Contributors:
#     James Jenkins (aka: themind)
####################

import csv
import time
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


def GetActiveMacs(fp):
    """Return a dict of {mac: lease_start_timestamp} for all active leases.

    Parses Kea DHCP4 memfile CSV. A lease is active if state == 0
    (STATE_DEFAULT) and the expiry timestamp is in the future.

    Lease start is approximated as expire - valid_lifetime.
    """
    now = time.time()
    ignore_macs = GetIgnoreMacs()
    result = {}

    reader = csv.DictReader(fp)
    for row in reader:
        try:
            if int(row["state"]) != 0:
                continue
            expire = int(row["expire"])
            if expire <= now:
                continue
            mac = row["hwaddr"].lower()
            if mac in ignore_macs:
                continue
            valid_lifetime = int(row["valid_lifetime"])
            lease_start = expire - valid_lifetime
            if mac not in result or lease_start < result[mac]:
                result[mac] = lease_start
        except (KeyError, ValueError):
            continue

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
    with open("dhcp4.leases") as f:
        print(GetActive(f))
