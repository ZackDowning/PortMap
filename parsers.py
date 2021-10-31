from net_async import multithread
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from datetime import datetime
import re


class RouterParser:
    """
Parses device to check if it is a router, connected networks, and arp cache.
    Parameters:
        session = Netmiko Connect Handler

        intfs = output of 'show ip interface'

        sh_routing = output of 'show run | i routing'

    Attributes:
        check = bool(if device is router)

        arp_table = list(output of 'show ip arp')

        networks = list(connected networks)
"""
    def __init__(self, session, intfs, sh_routing):


        def router_details():



        self.check = router_check()


class PortParser:
    """
    Parses outputs of commands: 'show cdp neighbor', 'show interface switchport', and 'show mac address-table'.
        Attributes:
            phones = []\n
            routers_switches = []\n
            waps = []\n
            others = []\n
        Dictionary format within lists:
            {
                'device
                'hostname',\n
                'ip_address',\n
                'model',\n
                'software_version',\n
                'neighbor': { (on router_switch, intfs are not in 'neighbor')
                    'hostname',\n
                    'ip_address',\n
                    'remote_intf', (neighbor interface)\n
                    'local_intf', (local to device, not on wap or phone)\n
                }\n
                'mac_addr', (phone only)\n
                'voice_vlan', (phone only)
            }
    """

    def __init__(self, cdp_neighbors, switchports, mac_addrs, session):
        nxos = False
        try:
            _ = cdp_neighbors[0]['destination_host']
        except KeyError:
            nxos = True

        self.switchports = []

        # multithread(parse, cdp_neighbors)


def output_to_spreadsheet(devices, failed_devices, file_location):
    """Parses device list and outputs to spreadsheet"""
    # Creates Excel workbook and worksheets
    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = 'Summary'
    # Create unique worksheets for each device here
    failed_ws = wb.create_sheet('Failed')

    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def write_header(worksheet, device_type):
        """
        :param device_type: 'Switch' or 'Failed'
        :param worksheet: Device worksheet
        :return: int(header_length), list(header)
        """
        header = ['Hostname', 'IP Address', 'Model', 'Software Version']
        if device_type == 'Switch':
            header += ['Serial', 'Connection Type', 'ROMMON', 'Connection Attempt', 'Discovery Status']
            for n in range(1, neighbor_count + 1):
                header += [f'Neighbor {n} Hostname', f'Neighbor {n} IP Address', f'Local Interface to Neighbor {n}',
                           f'Neighbor {n} Interface']
        elif device_type == 'Failed':
            header = ['IP Address', 'Connection Type', 'Device Type', 'Connectivity', 'Authentication',
                      'Authorization', 'Discovery Status', 'Connection Exception']
        worksheet.append(header)
        return len(header), header

    def write_to_sheet(device_list, worksheet, device_type):
        """
        :param device_type: 'RouterSwitch', 'Phone', 'CUCMPhone', 'WAP', 'Other', or 'Failed'
        :param device_list: List of devices
        :param worksheet: Device worksheet
        :return: list(rows)
        """
        rows = []
        for device in device_list:
            if device_type != 'Failed':
                row = [device['hostname'], device['ip_address'], device['model'], device['software_version']]
                if device_type == 'RouterSwitch':
                    if 'serial' in device:
                        serial = device['serial']
                        connection_type = device['connection_type']
                        rommon = device['rommon']
                    else:
                        serial = 'Unknown'
                        connection_type = 'Unknown'
                        rommon = 'Unknown'
                    row += [serial, connection_type, rommon, device['connection_attempt'], device['discovery_status']]
                    if device['connection_attempt'] == 'Failed':
                        for neighbor in device['neighbors']:
                            row += [neighbor['hostname'], neighbor['ip_address'], neighbor['local_intf'],
                                    neighbor['remote_intf']]
                if device_type == 'Phone' or device_type == 'CUCMPhone':
                    neighbor = device['neighbor']
                    row += [device['voice_vlan'], device['mac_addr'], neighbor['hostname'], neighbor['ip_address'],
                            neighbor['remote_intf']]
                    if 'description' in device:
                        row += [device['description'], device['directory_number']]
                if device_type == 'WAP' or device_type == 'Other':
                    neighbor = device['neighbor']
                    row += [neighbor['hostname'], neighbor['ip_address'], neighbor['remote_intf']]
                    if device_type == 'Other':
                        row.append(neighbor['local_intf'])
            else:
                row = [device['ip_address'], device['connection_type'], device['device_type'], device['connectivity'],
                       device['authentication'], device['authorization'], device['discovery_status'],
                       device['exception']]
            worksheet.append(row)
            rows.append(row)
        return rows

    def complete_sheet(device_list, worksheet, device_type):
        """Completes workbook sheet"""
        column_num = len(device_list) + 1
        header_out = write_header(worksheet, device_type)
        header = header_out[1]
        header_length = header_out[0]
        letter = header_length - 1
        if letter > 25:
            column_letter = f'{alphabet[int(letter / 26) - 1]}{alphabet[letter % 26]}'
        else:
            column_letter = alphabet[letter]
        bottom_right_cell = f'{column_letter}{column_num}'
        rows = write_to_sheet(device_list, worksheet, device_type)

        # Creates table if there is data in table
        if len(device_list) != 0:
            table = Table(displayName=device_type, ref=f'A1:{bottom_right_cell}')
            style = TableStyleInfo(name='TableStyleMedium9', showFirstColumn=False, showLastColumn=False,
                                   showRowStripes=True, showColumnStripes=True)
            table.tableStyleInfo = style
            worksheet.add_table(table)

        # Sets column widths
        all_data = [header]
        all_data += rows
        column_widths = []
        for row in all_data:
            for i, cell in enumerate(row):
                if len(column_widths) > i:
                    if len(str(cell)) > column_widths[i]:
                        column_widths[i] = len(str(cell))
                else:
                    column_widths += [len(str(cell))]

        for i, column_width in enumerate(column_widths):
            if i > 25:
                l1 = f'{alphabet[int(i / 26) - 1]}{alphabet[i % 26]}'
            else:
                l1 = alphabet[i]
            worksheet.column_dimensions[l1].width = column_width + 3

    # complete_sheet(routers_switches, routers_switches_ws, 'RouterSwitch')
    complete_sheet(failed_devices, failed_ws, 'Failed')

    # Saves workbook
    date_time = datetime.now().strftime('%m_%d_%Y-%H_%M_%S')
    wb.save(f'{file_location}/port_map-{date_time}-.xlsx')
