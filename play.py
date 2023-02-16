""" Start play mode. """

import argparse
import logging
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
from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler
from PIL import Image
from torchvision import models, transforms

from imagenet_labels import classes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@contextmanager
def camera(
    width: int = 224,
    height: int = 224,
    fps: int = 36,
):
    log.info("Starting video capture")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    def get_frame() -> np.ndarray:
        ret, image = cap.read()
        if not ret:
            log.error("Failed to capture frame")
            return None
        # convert opencv output from BGR to RGB
        image = image[:, :, [2, 1, 0]]
        return image

    try:
        yield get_frame
    finally:
        log.info("Ended video capture")
        del cap


@contextmanager
def servos(
    # servo 001 - 57600bps MX106 protocol2.0 range 180 to 270
    s1_min=110,
    s1_max=180,
    # servo 002 - 57600bps MX106 protocol2.0 range 0 to 180
    s2_min=0,
    s2_max=180,
    # Timeout duration for servo moving to position
    move_timeout = 2,
    # DYNAMIXEL Protocol Version (1.0 / 2.0)
    # https://emanual.robotis.com/docs/en/dxl/protocol2/
    PROTOCOL_VERSION=2.0,
    # Define the proper baudrate to search DYNAMIXELs. Note that XL320's baudrate is 1 M bps.
    BAUDRATE=57600,
    # Factory default ID of all DYNAMIXEL is 1
    DXL_IDS=[1, 2],
    # Use the actual port assigned to the U2D2.
    # ex) Windows: "COM*", Linux: "/dev/ttyUSB*", Mac: "/dev/tty.usbserial-*"
    DEVICENAME='/dev/ttyUSB0',
    # MX series with 2.0 firmware update.
    ADDR_TORQUE_ENABLE=64,
    ADDR_GOAL_POSITION=116,
    ADDR_PRESENT_POSITION=132,
    # Refer to the Minimum Position Limit of product eManual
    DXL_MINIMUM_POSITION_VALUE=0,
    # Refer to the Maximum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE=4095,
    TORQUE_ENABLE=1,     # Value for enabling the torque
    TORQUE_DISABLE=0,     # Value for disabling the torque
    DXL_MOVING_STATUS_THRESHOLD=20,    # Dynamixel moving status threshold
):
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

    # normalize servo from [0, 1] to [min_degrees, max_degrees]
    def norm_s1_deg(x): return (x * (s1_max - s1_min)) + s1_min
    def norm_s2_deg(x): return (x * (s2_max - s2_min)) + s2_min

    # normalize servo from [min_degrees, max_degrees] to [min_pos, max_pos]
    def norm_s1_pos(x): return int(((x / 360.0) * (DXL_MAXIMUM_POSITION_VALUE -
                                                   DXL_MINIMUM_POSITION_VALUE)) + DXL_MINIMUM_POSITION_VALUE)

    def norm_s2_pos(x): return int(((x / 360.0) * (DXL_MAXIMUM_POSITION_VALUE -
                                                   DXL_MINIMUM_POSITION_VALUE)) + DXL_MINIMUM_POSITION_VALUE)

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

    def set_pos(dxl_id, dxl_goal_position):

        log.info("Moving servo %s to %s" % (dxl_id, dxl_goal_position))
        
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
            portHandler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_ENABLE)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % packetHandler.getRxPacketError(dxl_error))
        else:
            print("Dynamixel has been successfully connected")

        # Normalize goal positions using the minimum and maximum position values.
        if dxl_id == 1:
            dxl_goal_position = norm_s1_pos(norm_s1_deg(dxl_goal_position))
        elif dxl_id == 2:
            dxl_goal_position = norm_s2_pos(norm_s2_deg(dxl_goal_position))
        else:
            raise ValueError("Invalid servo id")

        # Write goal position
        dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(
            portHandler, dxl_id, ADDR_GOAL_POSITION, dxl_goal_position)
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % packetHandler.getRxPacketError(dxl_error))

        # Move to goal position with timeout
        timeout_start = time.time()
        while time.time() < timeout_start + move_timeout:
    
            # Read present position
            dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(
                portHandler, dxl_id, ADDR_PRESENT_POSITION)
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                print("%s" % packetHandler.getRxPacketError(dxl_error))

            print("[ID:%03d] GoalPos:%03d  PresPos:%03d" %
                    (dxl_id, dxl_goal_position, dxl_present_position))

            if not abs(dxl_goal_position - dxl_present_position) > DXL_MOVING_STATUS_THRESHOLD:
                break

    try:
        yield set_pos

    finally:
        log.info("Ending Servo communication")
        for DXL_ID in DXL_IDS:
            # Disable Dynamixel Torque
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
                portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)
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
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                             0.229, 0.224, 0.225]),
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
    # TODO: FPS for each component, profile
    started = time.time()
    last_logged = time.time()
    frame_count = 0

    with camera() as get_frame, servos() as set_pos, model() as (net, preprocess):
        while True:

            # Set servos to starting position
            set_pos(1, 0)
            set_pos(2, 0)

            # preprocess
            image = get_frame()
            input_tensor = preprocess(image)

            # create a mini-batch as expected by the model
            input_batch = input_tensor.unsqueeze(0)

            with torch.no_grad():
                output = net(input_batch)

            # print results
            top = list(enumerate(output[0].softmax(dim=0)))
            top.sort(key=lambda x: x[1], reverse=True)
            for idx, val in top[:3]:
                print(f"{val.item()*100:.2f}% {classes[idx]}")

            # TODO: Confidence as LED?

            num_classes = len(classes)
            # Goal position is confidence for class
            set_pos(1, top[0][1])
            # Goal position is index of class
            set_pos(2, top[0][0] / num_classes)


            # Calculate FPS
            frame_count += 1
            now = time.time()
            if now - last_logged > 1:
                print(f"{frame_count / (now-last_logged)} fps")
                last_logged = now
                frame_count = 0
