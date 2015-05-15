# Office Presence

## Currently running front-end example

stringy's fish bot is currently providing the front end to this API.

Example usage in IRC #geekboy:

`$office` will list the users presently in the office<br/>
`$office -r <MAC_ADDRESS>` will regiser a MAC address with the nick of the speaker<br/>
`$office -d <MAC_ADDRES>` to de-register a MAC-to-nick entry<br/>

**Note:** The registration will use your current nick and you can *only* make changes to that registration entry with that nick.


## API

The server is hosted at: magpie.dhcp.io

The following paths provide the various API functionality:

/json<br/>
**Returns:** `{"registered": [<list of registered users>], "others": #of-non-registered-users}`

/plain<br/>
**Returns:** nick1 nick2 nick3 Non-registered: #<br/>
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

- Potentially allow remove all macs associated with a nick just by passing the nick


## Contributers

- themind
- stringy
- sphinx

(Idea pulled from suggestion by bears on the wikipages.)

