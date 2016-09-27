#!/usr/bin/env python3

"""LXC container manager script."""


import argparse
import json
import lxc
import re


CONTAINER_ETH0 = """    address {}
    netmask 255.255.255.0
    network 192.168.0.0
    broadcast 192.168.0.255
    gateway 192.168.0.254
"""


def create_container(name, mac_addr, ipv4, gateway_ipv4, package_list):
    """Create a new LXC container."""
    c = lxc.Container(name)
    if c.defined:
        # Nuke existing container
        c.stop()
        c.destroy()
        c = lxc.Container(name)
    c.create(template='debian')
    c.clear_config()
    c.load_config()
    c.network.remove(0)
    c.network.add('veth')
    c.network[0].flags = 'up'
    c.network[0].link = 'lxcbr0'
    c.network[0].ipv4 = [ipv4]
    # c.network[0].ipv4_gateway = '192.168.1.254'  BUG
    c.set_config_item('lxc.network.0.ipv4.gateway', gateway_ipv4)
    c.network[0].hwaddr = mac_addr
    c.save_config()
    # Patch network configuration:
    CONTAINER_ROOTFS = '/var/lib/lxc/{}/rootfs'
    CONTAINER_NIC_CONF = CONTAINER_ROOTFS + '/etc/network/interfaces'
    with open(CONTAINER_NIC_CONF.format(name), 'r+') as f:
        fr = f.read()
        f.seek(0)  # overwrite contents
        f.write(re.sub('dhcp', 'static', fr))
        f.write(CONTAINER_ETH0.format(ipv4))
    c.start()
    c.attach_wait(lxc.attach_run_command, ['apt-get', 'update'])
    c.attach_wait(lxc.attach_run_command,
                  ['apt-get', '-y', 'install'] + package_list)
    return


def parse_cli():
    """Parse CLI options."""
    parser = argparse.ArgumentParser(
        description='Container management utility.')
    parser.add_argument('-f', '--file', help='JSON configuration file')
    return parser.parse_args()


def main():
    """CLI entry-point."""
    args = parse_cli()
    if args.file:
        with open(args.file) as f:
            cfg = json.load(f)
    else:
        return
    for c in cfg:
        create_container(c['name'], c['mac_addr'], c['ipv4_addr'],
                         c['ipv4_gw'], c['pkg_list'])


if __name__ == '__main__':
    main()
