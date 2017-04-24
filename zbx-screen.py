#!/usr/bin/env python3

import argparse
import json
import logging
import pprint
import pyzabbix
import yaml

def get_groupid(zapi, groupname):
    logging.info("Getting hostgroup of %s ..." % groupname)
    response = zapi.hostgroup.get(filter={'name': [groupname]})
    logging.info(response)
    return response[0]['groupid']

def get_hosts_in_group(zapi, groupid):
    logging.info("Getting hosts in group %s .." % groupid)
    response = zapi.host.get(groupids=groupid)
    hosts = sorted([(h['name'], h['hostid']) for h in response])
    logging.debug("hosts: %r" % hosts)
    return hosts

def get_graphs(zapi, hosts, items):
    logging.info("Getting graph list ..")
    graphids = []
    for host in hosts:
        logging.info("Getting graphs of: %s" % host[0])
        response = zapi.graph.get(hostids=host[1], filter={'name': items},
                sortfield="name", output="graphids")
        # pprint.pprint(response)
        graphids.extend(x['graphid'] for x in response)
    logging.info("graphids: %r" % graphids)
    return graphids

def get_screen(zapi, groupname, hsize, vsize):
    logging.info("Getting screen %s" % groupname)
    response = zapi.screen.get(filter={'name': groupname})
    logging.info(response)
    create_new = True
    if response:
        screenid = response[0]['screenid']
        old_hsize, old_vsize = int(response[0]['hsize']), int(response[0]['vsize'])
        if hsize != old_hsize or vsize != old_vsize:
            logging.info("Deleting screen: %s" % screenid)
            response = zapi.screen.delete(screenid)
            logging.info(response)
        else:
            create_new = False
    if create_new:
        logging.info("Creating screen %s" % groupname)
        response = zapi.screen.create(name=groupname, hsize=hsize, vsize=vsize)
        logging.info(response)
        screenid = response['screenids'][0]
    return screenid

def update_screen(zapi, screenid, graphids, vsize, hsize):
    screenitems = [{"resourcetype": 0, "resourceid": graphids[x+y*vsize],
                    "x": x, "y": y, "width": 500}
            for x in range(vsize) for y in range(hsize)]
    logging.info("Updating screen %s" % screenid)
    response = zapi.screen.update(screenid=screenid, screenitems=screenitems)
    logging.info(response)

def load_config(config_file):
    with open(config_file) as cf:
        config = yaml.safe_load(cf)
    logging.debug("Load config: %r" % config)
    return config

def main(args):
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
            format='%(asctime)s %(levelname)-8s %(message)s')

    config = load_config(args.config)

    # auth
    auth = config['auth']
    zapi = pyzabbix.ZabbixAPI(auth['host_url'])
    logging.info("Trying login ...")
    zapi.login(auth['username'], auth['password'])

    # group
    for group in config['groups']:
        items = group['items']
        names = group['names']
        for groupname in names:
            logging.info("##### Updating %s .. #####" % groupname)
            groupid = get_groupid(zapi, groupname)
            hosts = get_hosts_in_group(zapi, groupid)
            graphids = get_graphs(zapi, hosts, items)
            screenid = get_screen(zapi, groupname, len(items), len(hosts))
            update_screen(zapi, screenid, graphids, len(items), len(hosts))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ss manager agent")
    parser.add_argument("-c", "--config", default="zbx-screen.yaml", help="configure file")
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    args = parser.parse_args()
    print(args)
    main(args)

