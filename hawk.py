#!/usr/bin/env python2

# Contributers:
#     sphinx
#     themind (jpypi on Github)

import flask
import inroom
from re import compile as re_compile


app = flask.Flask(__name__)


FAIL = 'failure'
FAILURE = (FAIL, 400, [])


valid_mac_patt = re_compile("[:\-]".join(("[0-9a-fA-F]{2}",)*6))
def ValidateMac(mac_string):
    if valid_mac_patt.match(mac_string):
        return mac_string.replace("-", ":").lower()

    return False
        

@app.route('/reg', methods=['POST'])
def reg():
    mac_addr = ValidateMac(flask.request.form.get('mac', ''))
    nick = flask.request.form.get('nick', '')
    if mac_addr and nick:
        # The following may fail if someone tries to register over
        # someone else's MAC/nick
        if inroom.RegisterMac(mac_addr, nick):
            return 'success'

    return FAILURE


@app.route('/dereg', methods=['POST'])
def dereg():
    mac_addr = ValidateMac(flask.request.form.get('mac', ''))
    nick = flask.request.form.get('nick', '')

    # inroom.DeregisterMac returns True if it succeeded
    if mac_addr and nick and inroom.DeregisterMac(mac_addr, nick):
        return 'success'
    if nick:
        return FAIL #'success'

    return FAIL


#@app.route('/list', methods=['POST'])
#def list_nick_macs():
#    nick = flask.request.form.get('nick', '')
#    if nick:
#        mac_addresses = inroom.LookupNick(nick)
#        if mac_addresses:
#            return flask.json.dumps(mac_addresses)
#
#    return FAILURE

@app.route('/list/<nick>', methods=['GET'])
def list_nick_macs(nick):
    if nick:
        mac_addresses = inroom.LookupNick(nick)
        if mac_addresses:
            return flask.json.dumps(mac_addresses)

    return FAILURE


@app.route('/json')
def json_resp():
    leases = get_leases()
    response = {"registered": leases[0], "others": len(leases[1])}
    return flask.json.dumps(response)


@app.route('/plain')
def plain_resp():
    l = get_leases()
    non_registered = len(l[1])
    extra = ""
    if non_registered > 0:
        extra = " - Unregistered: %d"%non_registered
    return ", ".join(l[0])+extra


def get_leases():
    with open('dhcpd.leases') as f:
        return inroom.GetActive(f)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
