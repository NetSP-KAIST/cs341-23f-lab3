#!/usr/bin/python3

import pox.openflow.libopenflow_01 as of

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
# Task 4: Implementing simple DNS-based censorship 
#   - Let switches send all DNS packets to Controller
#       - Create proper forwarding rules, send all DNS queries and responses to the controller
#       - HTTP traffic should not be forwarded to the controller
#   - Check if DNS query contains cs341dangerous.com
#       - For such query, drop it and reply it with empty DNS response
#       - For all other packets, route them normally
#       
#
# Task 5: Implementing more efficient DNS-based censorship 
#   - Let switches send only DNS query packets to Controller
#       - Create proper forwarding rules, send only DNS queries to the controller
#   - Check if DNS query contains cs341dangerous.com
#       - If such query is found, insert a new rule to switch to track the DNS response
#           - let the swtich route DNS response to the controller
#       - When the corresponding DNS response arrived, do followings:
#           - parse DNS response, insert a new rule to block all traffic from/to the server
#           - reply the DNS request with empty DNS response
#       - For all other packets, route them normally


###
# If you want, you can define global variables, import libraries, or do others
###

from pox.lib.packet import ethernet
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
        msg.priority = 1
        msg.actions.append(of.ofp_action_output(port = port))
        connection.send(msg)
        # IPv4 rule
        msg = of.ofp_flow_mod()
        msg.match.dl_type = ethernet.IP_TYPE
        msg.match.nw_dst = hostip
        msg.priority = 0
        msg.actions.append(of.ofp_action_output(port = port))
        connection.send(msg)
    
    # DNS rule
    msg = of.ofp_flow_mod()
    msg.match.dl_type = ethernet.IP_TYPE
    msg.match.tp_dst = 53
    msg.priority = 1
    msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
    connection.send(msg)

from scapy.all import * # you can use scapy in this task

def handlePacket(switchname, event, connection):
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
    packetfrags = {}
    p = packet
    while p is not None:
        packetfrags[p.__class__.__name__] = p
        if isinstance(p, bytes):
            break
        p = p.next
    print(packet.dump()) # print out unhandled packets
    # How to know protocol header types? see name of class

    # If you want to send packet back to switch, you can use of.ofp_packet_out() message.
    # Refer to [ofp_packet_out - Sending packets from the switch](https://noxrepo.github.io/pox-doc/html/#ofp-packet-out-sending-packets-from-the-switch)
    # You may learn from [l2_learning.py](pox/pox/forwarding/l2_learning.py), which implements learning switches

    global bestport

    relayPacket = True # whether to relay this packet

    if 'ipv4' in packetfrags.keys() and 'dns' in packetfrags.keys():
        # DNS packet
        for question in packetfrags['dns'].questions:
            if question.name == 'cs341dangerous.com':
                # Insert routing rule to hijack DNS response
                msg = of.ofp_flow_mod()
                msg.match.dl_type = ethernet.IP_TYPE
                msg.match.nw_dst = packetfrags['ipv4'].srcip
                msg.match.nw_src = packetfrags['ipv4'].dstip
                msg.match.tp_src = 53
                msg.priority = 10
                msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
                connection.send(msg)
        for answer in packetfrags['dns'].answers:
            if answer.name == 'cs341dangerous.com':
                relayPacket = False # do not relay this packet

                ## Create and Send Empty DNS Response
                pkt = Ether(event.ofp.data)
                pkt.build()
                pkt[DNS].ancount = 0
                pkt[DNS].an = None
                del pkt[IP].len
                del pkt[IP].chksum
                del pkt[UDP].len
                del pkt[UDP].chksum
                pkt.build()
                raw(pkt)
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(packetfrags['ipv4'].dstip)]))
                msg.data = raw(pkt)
                msg.in_port = event.port
                connection.send(msg)

                ## Block All Traffic from the dangerous IP
                dangerousIP = answer.rddata
                
                ### Block traffic to the dangerous IP
                msg = of.ofp_flow_mod()
                msg.match.dl_type = ethernet.IP_TYPE
                msg.match.nw_dst = str(dangerousIP)
                msg.priority = 10
                # no action; drop it
                connection.send(msg)

                ### Block traffic from the dangerous IP
                msg = of.ofp_flow_mod()
                msg.match.dl_type = ethernet.IP_TYPE
                msg.match.nw_src = str(dangerousIP)
                msg.priority = 10
                # no action; drop it
                connection.send(msg)
    
    if relayPacket and 'ipv4' in packetfrags.keys():
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(port = bestport[switchname][str(packetfrags['ipv4'].dstip)]))
        msg.data = event.ofp
        msg.in_port = event.port
        connection.send(msg)