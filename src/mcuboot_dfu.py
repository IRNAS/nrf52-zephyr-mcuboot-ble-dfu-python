"""
Perform MCUBoot DFU using the mcumgr-cli tool: https://github.com/apache/mynewt-mcumgr-cli.
To install the tool run install.sh found in this repository.
Tested with python 3.7+
"""

import logging
import subprocess
import json
import time

from zephyr_mcuboot_dfu.src.analyze_mcuboot_img import get_image_hash
from zephyr_mcuboot_dfu.src.util import run_command

RC_COUNT = 5

class MCUBootDFU():
    def __init__(self, device_name, image_path):
        """Initialize MCUBootDFU class with device name and path to image"""
        self.device_name = device_name
        self.image_path = image_path

        self.image_data_dict = {
            "image": "",
            "slot": "",
            "version": "",
            "bootable": "",
            "flags": "",
            "hash": ""
        }

    def __del__(self):
        """Cleanup"""
        # NOTE: it appears we need to restart the hci0 interface each time we perform the dfu
        # TODO: figure out why?
        process = subprocess.Popen("hciconfig hci0 reset".split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        process.kill()


    def _parse_value(self, attribute, line, delimiter):
        """Parse value from string, select value with attribute"""
        if attribute in line:
            split_line = line.split(delimiter)
            if len(split_line) > 1:
                self.image_data_dict[attribute] = split_line[1].strip()
        else:
            return False

    def get_image_list_json(self, image_list_string):
        """Return json object with image list parameters"""

        # sanitize string and split it into array
        split = image_list_string.replace("  ", "").split("\n")
        split = [line.strip() for line in split]

        images = []

        index = 0
        if split[index] == "Images:":
            index += 1

            # decode inner string
            while "image" in split[index] and "slot" in split[index]:
                line = split[index]
                header = line.split(" ")
                self._parse_value("image", header[0], "=")
                self._parse_value("slot", header[1], "=")
                index += 1  # move to "version"

                # extract version
                line = split[index]
                self._parse_value("version", line, ":")
                index += 1  # move to "bootable"

                line = split[index]
                self._parse_value("bootable", line, ":")
                index += 1  # move to "flags"

                line = split[index]
                # print(line)
                if "flags" in line:
                    bootable_split = line.split(":")
                    if len(bootable_split) > 1:
                        self.image_data_dict["flags"] = [flag for flag in bootable_split[1].strip().split(" ") if len(flag) > 1]
                else:
                    return images
                index += 1  # move to "hash"

                line = split[index]
                self._parse_value("hash", line, ":")
                index += 1  # end 

                images.append(self.image_data_dict)  # append found image to image list

                # reset dict
                self.image_data_dict = {
                    "image": "",
                    "slot": "",
                    "version": "",
                    "bootable": "",
                    "flags": "",
                    "hash": ""
                }

            return images  # return list of images when done
        else:
            return images

    def list_device_images(self, device_name):
        """Return list of device images"""
        image_list = run_command(device_name, "image list")
        listed_images = None
        if image_list is not None:  # if image list succeeded continue
            listed_images = self.get_image_list_json(image_list)
        return listed_images

    def get_image_data(self, listed_images, file_hash):
        """Return tuple of True/False and image data if True"""
        image_exists = False
        image_data = None
        for image in listed_images:
            if image["hash"] == file_hash:
                image_exists = True
                image_data = image

        return image_exists, image_data

    def perform_dfu(self):
        """Perform mcuboot dfu"""
        # 0. get hash of selected image
        file_hash = get_image_hash(self.image_path)
        logging.info(f"SHA256 of file to upload: {file_hash}")

        while True:
            rc = 0
            while rc < RC_COUNT:
                # list images on device
                listed_images = self.list_device_images(self.device_name)
                # print(f"Images found on device: {listed_images}")
                if listed_images is None:
                    rc += 1
                else:
                    break

                time.sleep(10)  # wait 10 seconds before trying again

            if rc >= RC_COUNT:
                logging.warning("DFU process failed. Returning False")
                return False  # DFU failed
            else:
                logging.debug(f"Image list: {listed_images}")

            # check if hash of image we're uploading is already on device
            image_exists, image_data = self.get_image_data(listed_images, file_hash)
            logging.info(f"Image exists: {image_exists}, data: {image_data}")

            # if image already on device 
            if image_exists:
                logging.info("Image exists on device!")

                # check if image already in slot 0
                if int(image_data["slot"]) == 0:
                    logging.debug(f"Image in slot 0. Flags: {image_data['flags']}")
                    # check if image flag is active and confirmed
                    if "active" in image_data["flags"] and "confirmed" in image_data["flags"]:
                        logging.info(f"DFU process succeeded. Returning True")
                        return True  # image already running on slot 0
                        
                    # check if image is only confirmed - make it active
                    if "active" in image_data["flags"] and len(image_data["flags"]) == 1:
                        logging.info("Confirming image and resetting device")
                        run_command(self.device_name, "image confirm", image_data["hash"])  # TODO check output
                        run_command(self.device_name, "reset")  # reset device

                # check if image in slot 1
                if int(image_data["slot"]) == 1:
                    logging.debug(f"Image in slot 1. Flags: {image_data['flags']}")
                    # check if state of image is not set
                    if len(image_data["flags"]) == 0:
                        # confirm image
                        image_hash = image_data["hash"]
                        logging.info("Testing image and resetting device")
                        run_command(self.device_name, "image test", image_hash)  # test image
                        run_command(self.device_name, "reset")  # reset device

            # if image not on device
            if not image_exists:
                logging.info(f"Selected image not found. Starting image upload...")
                logging.info(f"This can take up to a few minutes")
                run_command(self.device_name, "image upload", self.image_path)