# Office Presence
## Running

To run the office presence service one can simple run `api.py` directly, or use
`api.wsgi` behind apache or nginx via the uwsgi moduals.

A symlink is expecte in the working directory of the api named `dhcpd.leases`.
This link should point to a dhcpd leases file. Example:
```
$ ln -s /var/lib/dhcp/dhcpd.leases dhcpd.leases
```

While running this service it may be necessary to blacklist certain MAC
addresses such as addresses which are always in the room. (e.g. various desktops
or other servers on the network) To do this, create a file named
`ignorelist.config`, and place it in the current working directory. The contents
must be a single MAC address per line. Lines starting with `#` will be treated
as a comment line and can be used to describe what device a specific MAC belongs
to and why it's being filtered out.

## Frontend Chatbot Example UI

Usage in IRC (Through stringy's fish bot.):

`$office` will list the users presently in the office<br/>
`$office -r <MAC_ADDRESS>` will regiser a MAC address with the nick of the speaker<br/>
`$office -d <MAC_ADDRES>` to de-register a MAC-to-nick entry<br/>

**Pro-tip:** *fish* can be used via pm and doing so may reduce the amount of pinging and filling of highmons of people currently in club.

**Notes:** The registration will use your current nick and you can *only* make changes to that registration entry with that nick.


## API

The server is hosted at: `magpie.dhcp.io`

The following paths on the server provide the following API functionality:

/json<br/>
**Returns:** `{"registered": [<list of registered users>], "others": #of-non-registered-users}`

/plain<br/>
**Returns:** `nick1 nick2 nick3 Non-registered: #`<br/>
**Notes:** The return is a space seperated list of nicks as well as the number of non-registered users presently on the network.

/reg<br/>
**POST args:** `nick & mac`<br/>
**Returns:** `success` or `failure`<br/>
**Notes:** Both nick and mac are required. `mac` must be a valid MAC address.<br/>

/dereg<br/>
**POST args:** `nick & mac`<br/>
**Returns:** `success` or `failure`<br/>
**Notes:** This will de-register a MAC address to nick association based on the MAC. *Only one* MAC will be removed. The nick *must* match the one associated with the MAC address.

/list<br/>
**POST args:** `nick`<br/>
**Returns:** `["MAC1","MAC2"]`<br/>
**Notes:** The return is a json list of MAC addresses registered under a particular username.


## Todo

- Potentially be able to remove all macs associated with a nick just by passing the nick


## Contributers

- themind
- stringy
- sphinx

(Idea pulled from suggestion by bears on the club wiki pages.)

