#!/usr/bin/python3

import pox.openflow.libopenflow_01 as of

from pox.lib.packet import ethernet

# KAIST CS341 SDN Lab Task 2, 3, 4
#
# All functions in this file runs on the controller:
#   - init(net):
#       - runs only once for network, when initialized
#       - the controller should process the given network structure for future behavior
#   - addrule(switchname, connection):
#       - runs when a switch connects to the controller
#       - the controller should insert routing rules to the switch
#   - handlePacket(packet, connection):
#       - runs when a switch sends unhandled packet to the controller
#       - the controller should decide whether to handle the packet:
#           - let the switch route the packet
#           - drop the packet
#
# Task 2: Getting familiarized with POX 
#   - Let switches "flood" packets
#   - This is not graded
# 
# Task 3: Implementing a Simple Routing Protocol
#   - Let switches route via Dijkstra
#   - Match ARP and ICMP over IPv4 packets
#
# Task 4: Implementing simple DNS censorship 
#   - Let switches send DNS packets to Controller
#       - By default, switches will send unhandled packets to controller
#   - Drop DNS requests for asking cs341dangerous.com, relay all other packets correctly
#
# Task 5: Implementing simple HTTP censorship 
#   - Let switches send HTTP packets to Controller
#       - By default, switches will send unhandled packets to controller
#   - Additionally, drop HTTP requests for heading cs341dangerous.com, relay all other packets correctlys


###
# If you want, you can define global variables, import libraries, or do others
###

from queue import PriorityQueue

bestport = {}

def init(net) -> None:
    #
    # net argument has following structure:
    # 
    # net = {
    #    'hosts': {
    #         'h1': {
    #             'name': 'h1',
    #             'IP': '10.0.0.1',
    #             'links': [
    #                 # (node1, port1, node2, port2, link cost)
    #                 ('h1', 1, 's1', 2, 3)
    #             ],
    #         },
    #         ...
    #     },
    #     'switches': {
    #         's1': {
    #             'name': 's1',
    #             'links': [
    #                 # (node1, port1, node2, port2, link cost)
    #                 ('s1', 2, 'h1', 1, 3)
    #             ]
    #         },
    #         ...
    #     }
    # }
    #
    ###
    # YOUR CODE HERE
    ###

    ## We will save data in this object
    global bestport

    ## For all switches, pre-compute best link for hosts
    for switchname, switchinfo in net['switches'].items():
        bestport[switchname] = {}
        # intiialize distance to self = 0
        distance = {switchname: 0}
        visited = set([switchname])
        # Initialize Priority Queue used for Dijkstra
        #   Item format: (cost, node name, port)
        PQ = PriorityQueue()
        # Directly connected nodes' distance is known
        for [node1, port1, node2, port2, cost] in switchinfo['links']:
            if node1 == switchname:
                PQ.put((cost, node2, port1))
                distance[node2] = cost
            else:
                PQ.put((cost, node1, port2))
                distance[node1] = cost
        while not PQ.empty():
            cost, nodename, port = PQ.get()
            if nodename in visited:
                # already visited node
                continue
            visited.add(nodename)

            # If the node is a host, record port choice
            if nodename[0] == 'h':
                bestport[switchname][net['hosts'][nodename]['IP']] = port
            
            # If the node is a switch, look around to add nodes into the queue
            if nodename[0] == 's':
                for [node1, port1, node2, port2, linkcost] in net['switches'][nodename]['links']:
                    newcost = cost + linkcost
                    if node1 == nodename:
                        if node2 not in distance.keys() or distance[node2] > newcost:
                            PQ.put((newcost, node2, port))
                            distance[node2] = newcost
                    else:
                        if node1 not in distance.keys() or distance[node1] > newcost:
                            PQ.put((newcost, node1, port))
                            distance[node1] = newcost



def addrule(switchname: str, connection) -> None:
    #
    # This function is invoked when a new switch is connected to controller
    # Install table entry to the switch's routing table
    #
    # For more information about POX openflow API,
    # Refer to [POX official document](https://noxrepo.github.io/pox-doc/html/),
    # Especially [ofp_flow_mod - Flow table modification](https://noxrepo.github.io/pox-doc/html/#ofp-flow-mod-flow-table-modification)
    # and [Match Structure](https://noxrepo.github.io/pox-doc/html/#match-structure)
    #
    # your code will be look like:
    # msg = ....
    # connection.send(msg)
    ###
    # YOUR CODE HERE
    ###
    global bestport
    for hostip, port in bestport[switchname].items():
        # ARP rule
        msg = of.ofp_flow_mod()
        msg.match.dl_type = ethernet.ARP_TYPE
        msg.match.nw_dst = hostip
        msg.actions.append(of.ofp_action_output(port = port))
        connection.send(msg)
        # ICMP over IPv4 rule
        msg = of.ofp_flow_mod()
        msg.match.dl_type = ethernet.IP_TYPE
        msg.match.nw_proto = 0x01 # ICMP
        msg.match.nw_dst = hostip
        msg.actions.append(of.ofp_action_output(port = port))
        connection.send(msg)

def handlePacket(switchname, event, connection):
    global bestport
    packet = event.parsed
    if not packet.parsed:
        print('Ignoring incomplete packet')
        return
    # Retrieve how packet is parsed
    # Packet consists of:
    #  - various protocol headers
    #  - one content
    # For example, a DNS over UDP packet consists of following:
    # [Ethernet Header][           Ethernet Body            ]
    #                  [IPv4 Header][       IPv4 Body       ]
    #                               [UDP Header][ UDP Body  ]
    #                                           [DNS Content]
    # POX will parse the packet as following:
    #   ethernet --> ipv4 --> udp --> dns
    # If POX does not know how to parse content, the content will remain as `bytes`
    #     Currently, HTTP messages are not parsed, remaining `bytes`. you should parse it manually.
    # You can find all available packet header and content types from pox/pox/lib/packet/
    packetfrags = []
    p = packet
    while p is not None:
        packetfrags.append(p)
        if isinstance(p, bytes):
            break
        p = p.next
    print(packet.dump()) # print out unhandled packets
    # How to know protocol header types? see name of class
    # print('-->'.join(map(lambda obj:obj.__class__.__name__, packetfrags)))

    # If you want to send packet back to switch, you can use of.ofp_packet_out() message.
    # Refer to [ofp_packet_out - Sending packets from the switch](https://noxrepo.github.io/pox-doc/html/#ofp-packet-out-sending-packets-from-the-switch)
    # You may learn from [l2_learning.py](pox/pox/forwarding/l2_learning.py), which implements learning switches
    msg = of.ofp_packet_out()
    msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
    msg.data = event.ofp
    msg.in_port = event.port
    connection.send(msg)

    isIPv4 = any(map(lambda obj: obj.__class__.__name__ == 'ipv4', packetfrags))
    isTCP = any(map(lambda obj: obj.__class__.__name__ == 'tcp', packetfrags))
    isDNS = any(map(lambda obj: obj.__class__.__name__ == 'dns', packetfrags))
    includeAttacker = False
    # if any(map(lambda obj: obj.__class__.__name__ == 'dns', packetfrags)):
    
    srcip = None
    dstip = None
    
    for packetfrag in packetfrags:
        if packetfrag.__class__.__name__ == 'ipv4':
            print('packet from {} to {}'.format(packetfrag.srcip, packetfrag.dstip))
            srcip = packetfrag.srcip
            dstip = packetfrag.dstip
        if packetfrag.__class__.__name__ == 'dns':
            for question in packetfrag.questions:
                print('question - name: {} / rrtype: {} / rrclass: {}'.format(
                    question.name, question.qtype, question.qclass))
                if question.name == 'cs341dangerous.com':
                    includeAttacker = True
            for answer in packetfrag.answers:
                print('answer - name: {} / rrtype: {} / rrclass: {} / data: {}'.format(
                    answer.name, answer.qtype, answer.qclass, answer.rddata))
    if isDNS and not includeAttacker:
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
        msg.data = event.ofp
        msg.in_port = event.port
        connection.send(msg)
    if isIPv4 and isTCP and packetfrags[-1].__class__ == bytes:
        # maybe HTTP?
        print(packetfrags[-1])
        if packetfrags[-1].startswith(b'HTTP'):
            # This is HTTP response
            # print(packetfrags[-1])
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
            msg.data = event.ofp
            msg.in_port = event.port
            connection.send(msg)
        elif packetfrags[-1].startswith(b'GET'):
            # This is HTTP GET
            isAttacker = False
            for line in packetfrags[-1].splitlines():
                linestrip = line.strip()
                if linestrip.startswith(b'Host: '):
                    if linestrip[6:] == b'cs341dangerous.com':
                        isAttacker = True
                    break
            if not isAttacker:
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
                msg.data = event.ofp
                msg.in_port = event.port
                connection.send(msg)
        elif packetfrags[-1].startswith(b'POST'):
            isAttacker = False
            for line in packetfrags[-1].splitlines():
                linestrip = line.strip()
                if linestrip.startswith(b'Host: '):
                    if linestrip[6:] == b'cs341dangerous.com':
                        isAttacker = True
                    break
            if not isAttacker:
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
                msg.data = event.ofp
                msg.in_port = event.port
                connection.send(msg)
        else:
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(dstip)]))
            msg.data = event.ofp
            msg.in_port = event.port
            connection.send(msg)