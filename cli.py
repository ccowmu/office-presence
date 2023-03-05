#!/usr/bin/python

import dhcpreg
import json
from pprint import pprint

menu="""1 > View registered users
2 > Register new user
3 > Deregister user via MAC
4 > Look up MACs registerd under a nick
q > quit"""

while True:
    print menu
    try:
        choice = raw_input(">> ")
        if choice == "q": break
        choice = int(choice)
    except ValueError:
        continue

    print

    if choice==2:
        name = raw_input("Username: ")
        mac  = raw_input("Mac Address: ")
        print dhcpreg.RegisterMac(mac,name)

    if choice==1:
        f=open("registrations.config")
        pprint(json.load(f))
        f.close()

    if choice==3:
        mac  = raw_input("Mac Address: ")
        name = dhcpreg.LookupMac(mac)

        if name:
            print("Removing user: {}".format(name))
            dhcpreg.DeregisterMac(mac,name)

        else:
            print("Error: User not found.")

    if choice == 4:
        name = raw_input("Username: ")
        pprint(dhcpreg.LookupNick(name))

    # Print out a nice newline
    print
