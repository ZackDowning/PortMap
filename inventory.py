# from parsers import PortParser
from net_async import AsyncSessions, BugCheck, InputError, ForceSessionRetry
# import time
# from ipaddress import IPv4Network

# TODO: Get list of active vlans and active interfaces for each vlan - add to summary
# TODO: Get list of active interfaces out of total available - add to summary
# TODO: Get POE capacity - add to summary
# TODO: Correlate MAC addresses to switchports
# TODO: Check if LLDP is enabled (if 'not enabled' or 'Invalid' is in cmd output)
# TODO: Correlate CDP / LLDP neighbors to all interfaces
# TODO: Dumb switch detection on access interfaces
"""DSD logic
If access interface:
    if voice vlan is configured:
        if voice vlan hosts > 1 - dumb switch
        if host vlan hosts == 2:
            check if one == mac address of voice vlan
        elif host vlan hosts > 2:
            dumb switch
    if lldp or cdp n
"""
# TODO: Aggregate info into master switchport list - add to summary


def discovery(session):
    """
    Function to run within ASyncSessions. Runs show commands and returns dictionary for each device eventually\n
    returned from ASyncSessions.\n
        :return:
            {
                'waps': cdp_parser.waps,
                'phones': cdp_parser.phones,
                'routers_switches': cdp_parser.routers_switches,
                'others': cdp_parser.others
            }"""
    try:
        cdp_neighbors = session.send_command('show cdp neighbor detail')
        lldp_neighbors = session.send_command('show lldp neighbor detail')
        switchports = session.send_command('show interface switchport')
        mac_addrs = session.send_command('show mac address-table | ex CPU')
        sh_ip_intf = session.send_command('show ip interface brief | exclude unassigned|down|Status')
        if type(sh_ip_intf) is not list:
            sh_ip_intf = sh_ip_intf.split('\n')
            if sh_ip_intf[len(sh_ip_intf) - 1] == '':
                sh_ip_intf.pop()
        if len(sh_ip_intf) > 1:
            router = True
        else:
            router = False
        cmds = [cdp_neighbors, switchports, mac_addrs, sh_ip_intf, lldp_neighbors]
        # port_parser = PortParser(cdp_neighbors, switchports, mac_addrs, sh_ip_intf, session)

        output = {
            'cdp_neighbors': cdp_neighbors,
            'switchports': switchports,
            'mac_addrs': mac_addrs
        }

        if router:
            if 'nxos' in session.devicetype:
                show_ip_arp = session.send_command('show ip arp vrf all')
                cmds += [show_ip_arp]
                output['arp_table'] = show_ip_arp
            else:
                show_vrf = session.send_command('show vrf')
                cmds += [show_vrf]
                show_ip_arp = []
                if type(show_vrf) is list:
                    for vrf in show_vrf:
                        show_ip_arp_vrf = session.send_command(f'show ip arp vrf {vrf["name"]}')
                        if type(show_ip_arp_vrf) is list:
                            show_ip_arp += show_ip_arp_vrf
                    output['arp_table'] = show_ip_arp

        if any('Authorization failed' in cmd for cmd in cmds):
            raise ForceSessionRetry
    except OSError:
        raise ForceSessionRetry

    return output


# class InventoryDiscovery:
#     """
#     Runs asynchronous discovery and collects inventory lists of phones, routers, switches, and other device types.
#
#     :parameter username: Username for device management
#     :parameter password: Password for device management
#     :parameter enable_pw: Enable Password
#     :parameter verbose: Prints progress of connections and discovery to screen
#     :parameter recursive: Runs additional dicovery passes on newly discovered devices not found within previously
#     scanned devices
#     """
#
#     def __init__(self, username, password, initial_mgmt_ips, enable_pw='', verbose=False, recursive=True):
#         self.routers_switches = []
#         """
#         Dictionary:
#             {'hostname',\n
#             'ip_address',\n
#             'software_version',\n
#             'model',\n
#             'discovery_status',\n
#             'connection_attempt',\n
#             'neighbors': [{
#                 'hostname',\n
#                 'ip_address',\n
#                 'remote_intf', (Local to neighbor)\n
#                 'local_intf', (Local to rt_sw)\n
#                }]}"""
#         self.waps = []
#         """
#         Dictionary:
#             {'hostname',\n
#             'neighbor': {
#                 'hostname',\n
#                 'ip_address',\n
#                 'remote_intf', (Local to AP)\n
#             },\n
#             'ip_address',\n
#             'software_version',\n
#             'model'}"""
#         self.phones = []
#         """
#         Dictionary:
#             {'hostname',\n
#             'neighbor': {
#                 'hostname',\n
#                 'ip_address',\n
#                 'remote_intf', (Local to phone)\n
#             },\n
#             'ip_address',\n
#             'mac_addr',\n
#             'voice_vlan',\n
#             'software_version',\n
#             'model'}"""
#         self.others = []
#         """
#         Dictionary:
#             {'hostname',\n
#             'ip_address',\n
#             'neighbor': {
#                 'hostname',\n
#                 'ip_address',\n
#                 'remote_intf', (Local to neighbor)\n
#                 'local_intf' (Local to 'other' device)
#             },\n
#             'software_version',\n
#             'model'}"""
#         self.failed_devices = []
#         """
#         Dictionary:
#             {'ip_address',\n
#             'connection_type',\n
#             'device_type',\n
#             'connectivity',\n
#             'authentication',\n
#             'authorization',\n
#             'exception',\n
#             'discovery_status'}"""
#
#         new_routers_switches = []
#         """Routers and switches discovered through CDP, not through SSH/TELNET"""
#         known_hostnames = []
#         """All known router and switcheshostnames"""
#         init = True
#         """Bool of initial discovery pass"""
#
#         # Changes logical variable name from initial name to match variable name for recursive discovery pass loop
#         # Also validates input
#         try:
#             if len(initial_mgmt_ips) == 0:
#                 raise InputError('No Management IP Addresses found')
#             else:
#                 mgmt_ips = initial_mgmt_ips
#                 """Device management IP addresses to run AsyncSessions on"""
#         except TypeError:
#             raise InputError('No Management IP Addresses found')
#
#         discovery_count = 1
#         """Discovery pass counter"""
#
#         def connection_sessions():
#             """Runs AsyncSessions with 'discovery' function on 'mgmt_ips'
#
#             :return: AsyncSessions(params)
#             """
#             while True:
#                 outputs = AsyncSessions(username, password, mgmt_ips, discovery, enable_pw, True)
#                 bug_check = BugCheck(outputs.successful_devices, outputs.failed_devices, mgmt_ips)
#                 if not bug_check.bug:
#                     break
#                 else:
#                     if verbose:
#                         print('Bug Found')
#             return outputs
#
#         def append_failed(failed_devices):
#             """Appends failed devices from 'connection_sessions()' to 'failed_devices'"""
#             if len(failed_devices) != 0:
#                 for failed_device in failed_devices:
#                     if init:
#                         failed_device['discovery_status'] = 'existing'
#                     else:
#                         failed_device['discovery_status'] = 'new'
#                     self.failed_devices.append(failed_device)
#
#         def append_endpoints(sessions_outputs):
#             """Apends WAPs, phones, and others to corresponding lists and device hostnames from init connections to
#             'known_hostnames' list"""
#             for output in sessions_outputs:
#                 output = output['output']
#                 for wap in output['waps']:
#                     self.waps.append(wap)
#                 for phone in output['phones']:
#                     self.phones.append(phone)
#                 for other in output['others']:
#                     self.others.append(other)
#
#         def remove_connection_discovered_new(device):
#             """Removes connection parsed device from 'new_routers_switches' list"""
#             for new_rt_sw in new_routers_switches:
#                 if device['ip_address'] == new_rt_sw['ip_address']:
#                     new_routers_switches.remove(new_rt_sw)
#                     break
#
#         def append_routers_switches(connection_parsed):
#             """Appends connection parsed device to 'routers_switches' list"""
#             for router_switch in connection_parsed:
#                 if init:
#                     router_switch['discovery_status'] = 'existing'
#                 else:
#                     router_switch['discovery_status'] = 'new'
#                 router_switch['connection_attempt'] = 'Success'
#                 known_hostnames.append(router_switch['hostname'])
#                 self.routers_switches.append(router_switch)
#                 remove_connection_discovered_new(router_switch)
#
#         def new_routers_switches_parse(new_cdp_routers_switches):
#             """Parses new routers and switches discovered from CDP appending to 'known_hostnames' list.\n
#             Also appends to 'new_routers_switches' list.
#
#             :return: new_ip_addresses
#             """
#             new_ip_addresses = []
#             for new_rt_sw in new_cdp_routers_switches:
#                 known_hostnames.append(new_rt_sw['hostname'])
#                 ip_address = new_rt_sw['ip_address']
#                 # Doesn't append blank IP address from CDP neighbor entry to new IP address list
#                 if ip_address != '':
#                     new_ip_addresses.append(ip_address)
#                 new_routers_switches.append(new_rt_sw)
#             return new_ip_addresses
#
#         start_full_discovery_time = time.perf_counter()
#
#         while True:
#             start_discovery_time = time.perf_counter()
#             if verbose:
#                 if init:
#                     print(f'=========================================================================\n'
#                           f'Starting Initial Discovery on {len(mgmt_ips)} Devices...\n'
#                           f'=========================================================================')
#                 else:
#                     print(f'-------------------------------------------------------------------------\n'
#                           f'Starting Discovery Pass #{discovery_count} on {len(mgmt_ips)} Devices...\n'
#                           f'-------------------------------------------------------------------------')
#
#             # Connects to devices
#             sessions = connection_sessions()
#
#             # Appends failed connection devices to 'failed_devices' list
#             append_failed(sessions.failed_devices)
#
#             # Appends non-router/switch devices to corresponding lists
#             append_endpoints(sessions.outputs)
#
#             # Seperates and formats previously connected to devices and devices discovered through CDP neighbors
#             rt_sw = RtSwSeperator(sessions.outputs, known_hostnames)
#
#             # Appends connection discovered devices to 'routers_switches' list
#             append_routers_switches(rt_sw.connection_parsed)
#
#             finish_discovery_time = time.perf_counter()
#             if verbose:
#                 discovery_elapsed_time = int(round((finish_discovery_time - start_discovery_time) / 60, 0))
#                 if init:
#                     if recursive:
#                         print(f'-------------------------------------------------------------------------\n'
#                               f'Finished Initial Discovery in {discovery_elapsed_time} Minutes\n'
#                               f'-------------------------------------------------------------------------\n')
#                 else:
#                     print(f'-------------------------------------------------------------------------\n'
#                           f'Finished Discovery Pass #{discovery_count} in {discovery_elapsed_time} Minutes\n'
#                           f'-------------------------------------------------------------------------\n')
#
#             # Ends discovery loop if recursive flag not true
#             if not recursive:
#                 break
#             # Checks if any new routers and switches discovered
#             elif len(rt_sw.new) != 0:
#                 # Re-defines 'mgmt_ips' list for next discovery pass and appends to 'new_routers_switches' list
#                 mgmt_ips = new_routers_switches_parse(rt_sw.new)
#                 discovery_count += 1
#                 init = False
#             # Ends discovery loop if no new routers and switches discovered
#             else:
#                 break
#
#         # Appends remaining failed connection CDP discovered routers and switches to final 'routers_switches' list
#         for new_router_switch in new_routers_switches:
#             new_router_switch['discovery_status'] = 'new'
#             new_router_switch['connection_attempt'] = 'Failed'
#             self.routers_switches.append(new_router_switch)
#
#         finish_full_discovery_time = time.perf_counter()
#         full_discovery_elapsed_time = int(round((finish_full_discovery_time - start_full_discovery_time) / 60, 0))
#         if verbose:
#             print(f'=========================================================================\n'
#                   f'Finished Full Discovery in {full_discovery_elapsed_time} Minutes\n'
#                   f'=========================================================================\n')
