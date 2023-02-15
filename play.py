""" Start play mode. """

import argparse
import os
import sys
import termios
import time
import tty
from contextlib import contextmanager


import cv2
import numpy as np
import torch
from dynamixel_sdk import *
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
from PIL import Image
from torchvision import models, transforms

from imagenet_labels import classes
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@contextmanager
def camera(*args, **kwds):
    log.info("Starting video capture")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
    cap.set(cv2.CAP_PROP_FPS, 36)
    try:
        yield cap
    finally:
        log.info("Ended video capture")
        del cap

@contextmanager
def servos():
    log.info("Starting Servo communication")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    
    # DYNAMIXEL Protocol Version (1.0 / 2.0)
    # https://emanual.robotis.com/docs/en/dxl/protocol2/
    PROTOCOL_VERSION            = 2.0

    # Define the proper baudrate to search DYNAMIXELs. Note that XL320's baudrate is 1 M bps.
    BAUDRATE                = 57600

    # Factory default ID of all DYNAMIXEL is 1
    DXL_IDS                      = [1, 2]

    # Use the actual port assigned to the U2D2.
    # ex) Windows: "COM*", Linux: "/dev/ttyUSB*", Mac: "/dev/tty.usbserial-*"
    DEVICENAME                  = '/dev/ttyUSB0'

    # MX series with 2.0 firmware update.
    ADDR_TORQUE_ENABLE          = 64
    ADDR_GOAL_POSITION          = 180 #116
    ADDR_PRESENT_POSITION       = 132
    DXL_MINIMUM_POSITION_VALUE  = 0         # Refer to the Minimum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE  = 4095      # Refer to the Maximum Position Limit of product eManual
    TORQUE_ENABLE               = 1     # Value for enabling the torque
    TORQUE_DISABLE              = 0     # Value for disabling the torque
    DXL_MOVING_STATUS_THRESHOLD = 20    # Dynamixel moving status threshold

    # Normalize goal positions using the minimum and maximum position values.
    normalize = lambda degrees: int((degrees / 360) * (DXL_MAXIMUM_POSITION_VALUE - DXL_MINIMUM_POSITION_VALUE) + DXL_MINIMUM_POSITION_VALUE)
    
    # Initialize PortHandler instance
    # Set the port path
    # Get methods and members of PortHandlerLinux or PortHandlerWindows
    portHandler = PortHandler(DEVICENAME)

    # Initialize PacketHandler instance
    # Set the protocol version
    # Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    # Open port
    if portHandler.openPort():
        log.info("Succeeded to open the port")
    else:
        log.info("Failed to open the port")
        log.info("Press any key to terminate...")
        getch()
        quit()

    # Set port baudrate
    if portHandler.setBaudRate(BAUDRATE):
        log.info("Succeeded to change the baudrate")
    else:
        log.info("Failed to change the baudrate")
        log.info("Press any key to terminate...")
        getch()
        quit()
            
    def goto(dxl_id, dxl_goal_position):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_ENABLE)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % packetHandler.getRxPacketError(dxl_error))
        else:
            print("Dynamixel has been successfully connected")

        # Normalize goal positions using the minimum and maximum position values.
        dxl_goal_position = normalize(dxl_goal_position)
        
        while 1:
            print("Press any key to continue! (or press ESC to quit!)")
            if getch() == chr(0x1b):
                break

            # Write goal position
            dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, dxl_id, ADDR_GOAL_POSITION, dxl_goal_position)
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                print("%s" % packetHandler.getRxPacketError(dxl_error))

            while 1:
                # Read present position
                dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION)
                if dxl_comm_result != COMM_SUCCESS:
                    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
                elif dxl_error != 0:
                    print("%s" % packetHandler.getRxPacketError(dxl_error))

                print("[ID:%03d] GoalPos:%03d  PresPos:%03d" % (dxl_id, dxl_goal_position, dxl_present_position))

                if not abs(dxl_goal_position - dxl_present_position) > DXL_MOVING_STATUS_THRESHOLD:
                    break


    try:
        yield goto

    finally:
        log.info("Ending Servo communication")
        for DXL_ID in DXL_IDS:
            # Disable Dynamixel Torque
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                print("%s" % packetHandler.getRxPacketError(dxl_error))


@contextmanager
def model(*args, **kwds):
    log.info("Starting AI model")
    torch.backends.quantized.engine = 'qnnpack'
    preprocess = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    net = models.quantization.mobilenet_v2(pretrained=True, quantize=True)
    # jit model to take it from ~20fps to ~30fps
    net = torch.jit.script(net)
    try:
        yield net, preprocess
    finally:
        log.info("Ended AI model")
        pass




if __name__ == '__main__':
    
    log.setLevel(logging.DEBUG)

    # Calculate FPS
    started = time.time()
    last_logged = time.time()
    frame_count = 0

    with camera() as c, servos() as goto, model() as (net, preprocess):
        while True:
            ret, image = c.read()
            if not ret:
                log.error("Failed to capture frame")
                break

            # convert opencv output from BGR to RGB
            image = image[:, :, [2, 1, 0]]
            
            # preprocess
            input_tensor = preprocess(image)

            # create a mini-batch as expected by the model
            input_batch = input_tensor.unsqueeze(0)

            with torch.no_grad():
                output = net(input_batch)

            goto(1, 180)
            goto(2, 180)

            # print results
            top = list(enumerate(output[0].softmax(dim=0)))
            top.sort(key=lambda x: x[1], reverse=True)
            for idx, val in top[:3]:
                print(f"{val.item()*100:.2f}% {classes[idx]}")
            
            # Calculate FPS
            frame_count += 1
            now = time.time()
            if now - last_logged > 1:
                print(f"{frame_count / (now-last_logged)} fps")
                last_logged = now
                frame_count = 0