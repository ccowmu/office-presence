#!/usr/bin/python

####################
# DHCP Lease parser to find leases that haven't expired
# and pair them up with registered MAC addresses
#
# Contributers:
#     James Jenkins (aka: themind)
####################

import re
import datetime
import json
import sys
import time


USERS_FILE = "registrations.config"


mac_patt   = re.compile("hardware ethernet ([0-9A-Fa-f:]+?);")
lease_patt = re.compile("lease ([0-9\.]+?) {(.+?)}", re.DOTALL)
start_time_patt = re.compile("starts [0-9] ([0-9:/ ]+?);")
end_time_patt   = re.compile("ends (?:[0-9] ([0-9:/ ]+?);|(never))")

def LoadRegistrations():
    try:
        with open(USERS_FILE, "r") as f:
            users=json.load(f)
            return users
    except (IOError, ValueError):
        return {}


def GetIgnoreMacs():
    try:
        with open("ignorelist.config","r") as f:
            # Only return non-comment lines. Beginning of line must
            # be a # (octothorpe) symbol
            return filter(lambda line: not line.lstrip().startswith("#"), \
                          f.read().strip().split("\n"))
    except IOError:
        sys.stderr.write("No ignorelist.config file\n")
        pass

    return []


def RegisterMac(mac,name):
    users = LoadRegistrations()

    if not users.get(mac.lower(), None):
        users[mac.lower()] = name
    else:
        return False

    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

    return True


def DeregisterMac(mac,nick):
    try:
        users = LoadRegistrations()
        if users[mac]==nick:
            del users[mac]
            with open(USERS_FILE, "w") as f:
                json.dump(users,f)

            return True

    except (IOError, ValueError, KeyError):
        # Just let the error drop through and return False
        pass

    return False


def LookupMac(mac):
    try:
        users = LoadRegistrations()
        return users[mac.lower()]
    except KeyError:
        return None


def LookupNick(nick):
    users = LoadRegistrations()
    macs = []
    for mac, reg_nick in users.iteritems():
        if reg_nick == nick:
            macs.append(mac)

    return macs


def GetActive(fp):
    data = fp.read()

    now = datetime.datetime.utcnow()
    ignore_macs = GetIgnoreMacs()
    active_users = []
    other_macs  = []

    utc_hours_offset = ((time.daylight and time.altzone) or time.timezone)/60/60
    utc_offset = datetime.timedelta(0, 0, 0, 0, 0, utc_hours_offset, 0)

    # Loop through leases in the leases file found by the regex
    for lease in lease_patt.findall(data):
        # Find the end time for the lease and convert it to a useable datetime
        end_time_s = end_time_patt.search(lease[1]).group(1)
        end_time = None
        if end_time_s and end_time_s != "never":
            end_time = datetime.datetime.strptime(end_time_s, "%Y/%m/%d %H:%M:%S")
        # Check that we haven't reached the end of this lease
        # make sure to account for UTC offset
        if end_time is None or now < end_time:
            # Pull the mac address from the lease with a regex
            lease_mac_address = mac_patt.findall(lease[1])
            # Make sure the regex actually found a mac address. Sometimes
            # a lease doesn't have one, so just ignore and skip to next one
            if not lease_mac_address:
                continue
            # regex.findall returns a list we just want the zeroth item
            lease_mac_address = lease_mac_address[0]
            if lease_mac_address not in ignore_macs:
                user = LookupMac(lease_mac_address)
                # If a registered user was found and not alreay active from
                # some other lease (possibly a secondary device).
                if user and user not in active_users:
                    active_users.append(user)
                # Keep track of non-registered mac addresses
                elif not user and lease_mac_address not in other_macs:
                    other_macs.append(lease_mac_address)

    return (active_users,other_macs)


if __name__ == "__main__":
    with open("/var/lib/dhcp/dhcpd.leases") as f:
        print GetActive(f)
