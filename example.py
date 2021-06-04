import logging
import argparse
import asyncio
import time
import sys
import os

from PyInquirer import prompt, style_from_dict, Token
from bleak import discover

from src.mcuboot_dfu import MCUBootDFU

def select_ble_device(devices):
    """Select device used for DFU"""

    if devices is not None:
    
        question_devices = [
            {
                "type": "list",
                "message": "Select discovered BLE device",
                "name": "device",
                "choices": [{"name": f"Address: {d.address}, Name: {d.name}", "value": d.name} for d in devices]
            }
        ]
        
        selected_device = prompt(question_devices)["device"]
        print(f"Selected device name: {selected_device}")
        return selected_device
    
    else:
        return None

def get_ble_devices(loop):
    """Finds all devices containg 'identifier' in name"""
    try:
        logging.info("Starting BLE device discovery")
        device_list = []
        async def run():
            devices = await discover(timeout=2)
            for d in devices:
                device_list.append(d)
        loop.run_until_complete(run())
        device_list.sort(key=lambda x: x.rssi)
    except Exception as e:
        logging.error(f"An exception occured during BLE device discovery: {e}")
        device_list = None
    return device_list


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.DEBUG)

parser = argparse.ArgumentParser(description="python3 example.py -f <hexfile> -d <dfu_target_name>")
parser.add_argument('-d', '--device', action='store', dest="device", default=None, help='DFU target name.')
parser.add_argument('-f', '--hexfile', action='store', dest="hexfile", default=None, help='Hex file to be used.')
args = parser.parse_args()

device = None
hexfile = None

if args.device is not None:
    device = args.device

if args.hexfile is not None:
    if os.path.exists(args.hexfile):
        hexfile = args.hexfile
    else:
        logging.warning("Specified hexfile not found! Exiting.")
        sys.exit(0)
else:
    logging.warning("Hexfile is not specified! Can not perform Secure DFU!")
    sys.exit(0)

if device is None:
    logging.warning("No device name specified.")
    time.sleep(1)
    loop = asyncio.get_event_loop()
    devices = get_ble_devices(loop)
    selected_device = select_ble_device(devices)
    if selected_device is not None:
        device = selected_device

if hexfile is not None and device is not None:
    # dfu sometimes fails, retry until it succeeds
    # TODO: find out WHY dfu fails
    success = False
    fail_counter = 0
    while not success:

        if fail_counter > 5:  # stop after 5 retries
            logging.error(f"Failed to perform DFU on device {device}. Exiting.")
            break
        
        try:
            # initialize dfu class
            dfu = MCUBootDFU(device, hexfile)
            ret = dfu.perform_dfu()
            success = ret
            if not success:
                fail_counter += 1
        except Exception as e:
            logging.error(f"Unable to perform dfu. Reason: {e}")
            
        time.sleep(1)

