#!/usr/bin/python3

#
# KAIST CS341 SDN Lab POX controller
# 

import json
import sys
import os

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import dns
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import task_controller # task_controller.py

log = core.getLogger()

net = None
switchcnt = 0

class CS341Switch(object):
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)

    # By default, switch will send unhandled packets to the controller
    def _handle_PacketIn(self, event):
        switchname = str(event.connection.ports[65534]).split(':',2)[0]
        task_controller.handlePacket(switchname, event, self.connection)

class CS341Controller(object):
    def __init__(self):
        core.openflow.addListeners(self)
    def routeinit(self):
        global net
        net = json.load(open('/tmp/net.json'))
        task_controller.init(net)
    def _handle_ConnectionUp(self, event):
        global net
        global switchcnt
        if switchcnt == 0:
            # This is the first switch
            self.routeinit()
        switchname = str(event.connection.ports[65534]).split(':',2)[0]
        task_controller.addrule(switchname, event.connection)
        switchcnt += 1
        if switchcnt == len(net['switches']):
            # This was the last switch
            switchcnt = 0
        CS341Switch(event.connection)
def launch():
    """
    Starts the component
    """
    core.registerNew(CS341Controller)
