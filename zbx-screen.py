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
        response = zapi.graph.get(hostids=host[1],
                filter={'name': items},
                sortfield="name",
                output="graphids")
        # pprint.pprint(response)
        graphids.extend(x['graphid'] for x in response)
    logging.info("graphids: %r" % graphids)
    return graphids

def get_screenid(zapi, screen_name):
    logging.info("Getting screen %s .." % screen_name)
    response = zapi.screen.get(filter={'name': screen_name})
    logging.info(response)
    if response:
        screenid = response[0]['screenid']
    else:
        logging.info("Creating screen %s .." % screen_name)
        response = zapi.screen.create(name=screen_name)
        logging.info(response)
        screenid = response['screenids'][0]
    return screenid

def update_screen(zapi, screenid, graphids, hsize):
    vsize = (len(graphids) + hsize - 1) // hsize
    screenitems = [{"resourcetype": 0, "resourceid": graphids[x+y*hsize],
            "x": x, "y": y, "width": 500, "height": 120}
            for x in range(hsize) for y in range(vsize) if (x+y*hsize) < len(graphids)]
    logging.info("Updating screen %s" % screenid)
    response = zapi.screen.update(screenid=screenid, screenitems=screenitems,
            hsize=hsize, vsize=vsize)
    logging.info(response)

def load_config(config_file):
    with open(config_file) as cf:
        config = yaml.safe_load(cf)
    logging.debug("Load config: %r" % config)
    return config

def get_host(zapi, hostname):
    logging.info("Getting hostinfo of %s" % hostname)
    response = zapi.host.get(filter={'name': hostname}, output=['name'])
    logging.info(response)
    return (response[0]['name'], response[0]['hostid'])

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
        if not group['names']: continue
        for groupname in group['names']:
            logging.info("##### Updating %s .. #####" % groupname)
            groupid = get_groupid(zapi, groupname)
            hosts = get_hosts_in_group(zapi, groupid)
            graphids = get_graphs(zapi, hosts, items)
            screenid = get_screenid(zapi, groupname)
            update_screen(zapi, screenid, graphids, len(items))

    # screens
    for screen in config['screens']:
        # pprint.pprint(screen)
        logging.info("##### Updating screen %s .. #####" % screen['name'])
        graphids = []
        for graph in screen['graphs']:
            host_name_ids = [get_host(zapi, hostname) for hostname in graph['hosts']]
            graphids.extend(get_graphs(zapi, host_name_ids, graph['items']))
        screenid = get_screenid(zapi, screen['name'])
        update_screen(zapi, screenid, graphids, screen['span'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ss manager agent")
    parser.add_argument("-c", "--config", default="zbx-screen.yaml", help="configure file")
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    args = parser.parse_args()
    print(args)
    main(args)

