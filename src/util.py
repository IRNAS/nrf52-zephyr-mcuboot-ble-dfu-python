"""
Defines functions used in the dfu process
"""
import subprocess
import time
import logging

def construct_command(device_name, command):
    """Return array of given command split by ' '. Should be passed as an argument to Popen"""
    # assumes mcumgr executable is located in folder
    # TODO: make mcumgr executable from installation location
    return f"./mcumgr --conntype ble --connstring peer_name={device_name} {command}".split(" ")  

def run_command(device_name, command, command_args=""):
    """Run mcumgr command with subprocess.Popen. If command takes additional parameters they have to be specified in command_args as a string split with ' '"""
    command_split = construct_command(device_name, f"{command} {command_args}")
    logging.debug(f"Sending command {command_split} to device {device_name}")

    process = subprocess.Popen(command_split, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    output_complete = ""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # print(output.strip())
            logging.debug(f"Popen output: {output}")
            output_complete += output
    rc = process.poll()

    time.sleep(3)
    
    if rc == 0:
        return output_complete
    else:
        return None