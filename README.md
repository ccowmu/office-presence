# Office Presence

## Currently running front-end example

stringy's fish bot is currently providing the front end to this API.

Example usage in IRC #geekboy:

`$office` will list the users presently in the office
`$office -r <MAC_ADDRESS>` for regisering
`$office -d <MAC_ADDRES>` to de-register

**Note:** The registration will use your current nick and you can *only* make changes to that registration entry with that nick.


## API

The server is hosted at: magpie.dhcp.io

The following paths provide the various API functionality:

/json
**Returns:** `{"registered": [<list of registered users>], "others": #of-non-registered-users}`

/plain
**Returns:** nick1 nick2 nick3 Non-registered: #
**Notes:** The return is a space seperated list of nicks as well as the number of non-registered users presently on the network.

/reg
**POST args:** `nick & mac`
**Returns:** `success` or `failure`
**Notes:** Both nick and mac are required. `mac` must be a valid MAC address.

/dereg
**POST args:** `nick & mac`
**Returns:** `success` or `failure`
**Notes:** This will de-register a MAC address to nick association based on the MAC. *Only one* MAC will be removed. The nick *must* match the one associated with the MAC address.

/list
**POST args:** `nick`
**Returns:** `["MAC1","MAC2"]`
**Notes:** The return is a json list of MAC addresses registered under a particular username.


## Todo

- Potentially allow remove all macs associated with a nick just by passing the nick


## Contributers

- themind
- stringy
- sphinx

(Idea pulled from suggestion by bears on the wikipages.)

