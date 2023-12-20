#!/usr/bin/python3

# KAIST CS341 SDN Lab Grader script

import time
import argparse
import sys
import random
import re
import signal
import subprocess
from io import BytesIO

from scapy.all import *

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel

from task_topology import Topology
from graph import gen_graph
from dump import dump_clear, dump_net

if __name__ == '__main__':
    # Uncomment below to see verbose log
    #setLogLevel('debug')
    
    parser = argparse.ArgumentParser(prog='CS341 SDN Lab Tester')
    parser.add_argument('--task', metavar='T', type=int, nargs='?', default=1,
                        help='task to test', required=True, choices=range(1,6))
    args = parser.parse_args()
    
    switches, hosts, links = gen_graph(args.task)
    if args.task == 1:
        t = Topology(switches, hosts, links)
        net = Mininet(topo=t)
    elif args.task in range(2, 6):
        t = Topology(switches, hosts, links)
        net = Mininet(topo=t, controller=RemoteController, listenPort=6633)
        dump_net(net, links)
    else:
        raise NotImplementedError('Supported Task number: 1-5')
    
    net.start()
    net.waitConnected(timeout=10)
    print('start grading for task {}'.format(args.task))
    if args.task == 4 or args.task == 5:
        # Launch DNS and HTTP server, then run client
        time.sleep(1)
        dangeroushost, safehost, dnshost, normalhost1, normalhost2, normalhost3 = random.sample(net.hosts, 6)
        # In order to write output to console: append argument (stdout=sys.stdout, stderr=sys.stderr)
        # popen('./server.py', shell=True, stdout=sys.stdout, stderr=sys.stderr)
        dangerousp = dangeroushost.popen('./server.py', shell=True)
        print('running cs341dangerous.com on {}({})'.format(dangeroushost.name, dangeroushost.IP()))
        safep = safehost.popen('./server.py', shell=True)
        print('running cs341safe.com on {}({})'.format(safehost.name, safehost.IP()))
        dnsp = dnshost.popen('./dns -a cs341dangerous.com={} -a cs341safe.com={}'.format(
            dangeroushost.IP(), safehost.IP()
        ), shell=True)
        time.sleep(3) # wait for servers and DNS to be ready
        print('running DNS on {}({})'.format(dnshost.name, dnshost.IP()))
        print('running normalhost1 on {}({})'.format(normalhost1.name, normalhost1.IP()))
        print('running normalhost2 on {}({})'.format(normalhost2.name, normalhost2.IP()))
        print('running normalhost3 on {}({})'.format(normalhost3.name, normalhost3.IP()))
        #print('You can test via following commands:')
        #print('{} dig @{} cs341safe.com'.format(normalhost.name, dnshost.IP()))
        #print('{} dig @{} cs341dangerous.com'.format(normalhost.name, dnshost.IP()))
        #print('{} curl -H "Host: cs341safe.com" -m 10 http://{}/'.format(normalhost.name, safehost.IP()))
        #print('{} curl -H "Host: cs341dangerous.com" -m 10 http://{}/'.format(normalhost.name, dangeroushost.IP()))
        if args.task == 4:
            ##########################################################################
            print('===DNS test with cs341safe.com===')
            cmd = 'dig @{} cs341safe.com'.format(dnshost.IP())
            p = normalhost1.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            answersection = False
            answerExist = False
            answerIPs = []
            for line in resp.splitlines():
                if answersection:
                    ls = line.strip()
                    if len(ls) != 0:
                        #  this is answer line
                        answerIPs.append(ls.split()[-1])
                    else:
                        # end of answer section
                        answersection = False
                if 'ANSWER SECTION' in line:
                    # next line is answer section
                    answersection = True
                    answerExist = True

            print('[TEST] Check if DNS Answer Section exist in DNS response')
            if answerExist:
                print('[PASS] DNS Answer section found for cs341safe.com')
                safeanswer = True
            else:
                print('[FAIL] DNS Answer section not found for cs341safe.com')
                safeanswer = False
            
            print('[TEST] Check if Correct IP exist in DNS response')
            if safehost.IP() in answerIPs:
                print('[PASS] Correct IP found for cs341safe.com')
                safeIP = True
            else:
                print('[FAIL] Correct IP not found for cs341safe.com')
                safeIP = False
            print('RAW DNS response:')
            print('{}:~/${}'.format(normalhost1.IP(), cmd))
            print(resp)
            ##########################################################################
            print('===DNS test with cs341dangerous.com===')
            cmd = 'dig @{} cs341dangerous.com'.format(dnshost.IP())
            p = normalhost2.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            answersection = False
            answerExist = False
            answerIPs = []
            for line in resp.splitlines():
                if answersection:
                    ls = line.strip()
                    if len(ls) != 0:
                        #  this is answer line
                        answerIPs.append(ls.split()[-1])
                    else:
                        # end of answer section
                        answersection = False
                if 'ANSWER SECTION' in line:
                    # next line is answer section
                    answersection = True
                    answerExist = True

            print('[TEST] Check if DNS Answer Section exist in DNS response')
            if answerExist:
                print('[FAIL] DNS answer found for cs341dangerous.com')
                dangerousanswer = True
            else:
                print('[PASS] DNS answer not found for cs341dangerous.com')
                dangerousanswer = False
            
            print('[TEST] Check if correct IP exist in DNS response')
            if dangeroushost.IP() in answerIPs:
                print('[FAIL] Correct IP found for cs341dangerous.com')
                dangerousIP = True
            else:
                print('[PASS] Correct IP not found for cs341dangerous.com')
                dangerousIP = False
            print('RAW DNS Response:')
            print('{}:~/${}'.format(normalhost2.IP(), cmd))
            print(resp)
            ##########################################################################
            print('Grading Policy:')
            grade = 0

            subgrade = 15 if not dangerousIP else 0
            print('[{}/15] Is IP of cs341dangerous.com not queryed?'.format(subgrade))
            grade += subgrade

            subgrade = 10 if not dangerousanswer else 0
            print('[{}/10] Is DNS Answer section correctly removed?'.format(subgrade))
            grade += subgrade

            subgrade = -25 if (not safeanswer or not safeIP) else 0
            print('[{}/-25] Is DNS for cs341safe.com broken?'.format(subgrade))
            grade += subgrade

            if grade < 0:
                grade = 0
            print('Grade of task 4:{}'.format(grade))
        elif args.task == 5:
            ##########################################################################
            tests = {
                'preHTTP': {
                    'safe': None,
                    'dangerous': None
                },
                'postHTTP': {
                    'safe': None,
                    'dangerous': None
                },
            }
            respPattern = re.compile(r'Hello 10\.0\.0\.\d*, I am cs341.+\.com\s*')
            ##########################################################################
            print('===HTTP test before DNS request===')

            print('[TEST] Check if cs341safe.com accessible')
            cmd = 'curl -H "Host: cs341safe.com" -m 10 http://{}/'.format(safehost.IP())
            p = normalhost1.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            if respPattern.match(resp):
                print('[PASS] cs341safe.com accessible')
                tests['preHTTP']['safe'] = True
            else:
                print('[FAIL] cs341safe.com inaccessible')
                tests['preHTTP']['safe'] = False
            print('Result of curl: ')
            print('{}:~/${}'.format(normalhost1.IP(), cmd))
            print(resp)
            
            print('[TEST] Check if cs341dangerous.com accessible')
            cmd = 'curl -H "Host: cs341dangerous.com" -m 10 http://{}/'.format(dangeroushost.IP())
            p = normalhost1.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            if respPattern.match(resp):
                print('[PASS] cs341dangerous.com accessible')
                tests['preHTTP']['dangerous'] = True
            else:
                print('[FAIL] cs341dangerous.com inaccessible')
                tests['preHTTP']['dangerous'] = False
            print('Result of curl:')
            print('{}:~/${}'.format(normalhost1.IP(), cmd))
            print(resp)
            ##########################################################################
            print('===DNS request for cs341safe.com===')
            cmd = 'dig @{} cs341safe.com'.format(dnshost.IP())
            p = normalhost2.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            print('Result of dig:')
            print('{}:~/${}'.format(normalhost2.IP(), cmd))
            print(resp)
            print('===DNS request for cs341dangerous.com===')
            cmd = 'dig @{} cs341dangerous.com'.format(dnshost.IP())
            p = normalhost2.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            print('Result of dig:')
            print('{}:~/${}'.format(normalhost2.IP(), cmd))
            print(resp)
            ##########################################################################
            time.sleep(3) # wait until controller installs rule into switch
            ##########################################################################
            print('===HTTP test after DNS request===')

            print('[TEST] Check if cs341safe.com accessible')
            cmd = 'curl -H "Host: cs341safe.com" -m 10 http://{}/'.format(safehost.IP())
            p = normalhost3.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            if respPattern.match(resp):
                print('[PASS] cs341safe.com accessible')
                tests['postHTTP']['safe'] = True
            else:
                print('[FAIL] cs341safe.com inaccessible')
                tests['postHTTP']['safe'] = False
            print('Result of curl: ')
            print('{}:~/${}'.format(normalhost3.IP(), cmd))
            print(resp)
            
            print('[TEST] Check if cs341dangerous.com accessible')
            cmd = 'curl -H "Host: cs341dangerous.com" -m 10 http://{}/'.format(dangeroushost.IP())
            p = normalhost3.popen(cmd, shell=True)
            resp = p.stdout.read().decode('utf-8')
            if respPattern.match(resp):
                print('[FAIL] cs341dangerous.com accessible')
                tests['postHTTP']['dangerous'] = True
            else:
                print('[PASS] cs341dangerous.com inaccessible')
                tests['postHTTP']['dangerous'] = False
            print('Result of curl:')
            print('{}:~/${}'.format(normalhost3.IP(), cmd))
            print(resp)
            ##########################################################################
            for cat, d in tests.items():
                for test, v in d.items():
                    if v == None:
                        print('[ERROR] tests[{}][{}] not checked'.format(cat, test))
                        
            print('Grading Policy:')
            grade = 0

            print('## HTTP Before DNS Query')
            subgrade = -25 if not tests['preHTTP']['safe'] else 0
            print('[{}/-25] Is IP of cs341safe.com not accessible?'.format(subgrade))
            grade += subgrade

            subgrade = -25 if not tests['preHTTP']['dangerous'] else 0
            print('[{}/-25] Is IP of cs341dangerous.com not accessible?'.format(subgrade))
            grade += subgrade

            print('## HTTP After DNS Query')
            subgrade = -25 if not tests['postHTTP']['safe'] else 0
            print('[{}/-25] Is cs341safe.com not accessible?'.format(subgrade))
            grade += subgrade

            subgrade = 25 if not tests['postHTTP']['dangerous'] else 0
            print('[{}/25] Is cs341dangerous.com not accessible?'.format(subgrade))
            grade += subgrade

            if grade < 0:
                grade = 0
            print('Grade of task 5:{}'.format(grade))
            
        ## check if accessing cs341safe.com and cs341dangerous.com is possible
        #normalhost.popen('curl -H "Host: cs341safe.com" -m 10 http://{}/'.format(safehost.IP()))
        ## check if DNS request is removed correctly

        ## check if now HTTP request is blocked correctly
        dangerousp.kill()
        safep.kill()
        dnsp.kill()
    else:
        droprate = net.pingAll()
        print('Grade of task {}:{}'.format(args.task, (100-droprate) / 4 ))
    net.stop()