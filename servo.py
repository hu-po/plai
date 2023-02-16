""" Main servo control class."""

import logging
import sys
import termios
import time
import tty
from contextlib import contextmanager
from typing import Dict, List, Tuple

from dynamixel_sdk import *
from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class Servo:

    def __init__(
        self,
        # Dynamixel servo ID
        id = 1,
        # Minimum angle of servo (degrees)
        min_degrees = 0,
        # Maximum angle of servo (degrees)
        max_degrees = 180,
        # Timeout duration for servo moving to position
        move_timeout=5,
        # DYNAMIXEL Protocol Version (1.0 / 2.0)
        # https://emanual.robotis.com/docs/en/dxl/protocol2/
        protocol_version=2.0,
        # Define the proper baudrate to search DYNAMIXELs.
        baudrate=57600,
        # Use the actual port assigned to the U2D2.
        # ex) Windows: "COM*", Linux: "/dev/ttyUSB*", Mac: "/dev/tty.usbserial-*"
        devicename='/dev/ttyUSB0',
        # MX series with 2.0 firmware update.
        addr_torque_enable=64,
        addr_goal_position=116,
        addr_present_position=132,
        # Refer to the Minimum Position Limit of product eManual
        dxl_minimum_position_value=0,
        # Refer to the Maximum Position Limit of product eManual
        dxl_maximum_position_value=4095,
        # Value for enabling the torque
        torque_enable=1,
        # Value for disabling the torque
        torque_disable=0,
        # Dynamixel moving status threshold
        dxl_moving_status_threshold=10,
    ):
        self.id = id
        self.min_degrees = min_degrees
        self.max_degrees = max_degrees
        self.move_timeout = move_timeout
        self.protocol_version = protocol_version
        self.baudrate = baudrate
        self.devicename = devicename
        self.addr_torque_enable = addr_torque_enable
        self.addr_goal_position = addr_goal_position
        self.addr_present_position = addr_present_position
        self.dxl_minimum_position_value = dxl_minimum_position_value
        self.dxl_maximum_position_value = dxl_maximum_position_value
        self.torque_enable = torque_enable
        self.torque_disable = torque_disable
        self.dxl_moving_status_threshold = dxl_moving_status_threshold

        self.torque_enabled = False

    def connect(self):

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

        # Initialize PortHandler instance
        # Set the port path
        # Get methods and members of PortHandlerLinux or PortHandlerWindows
        self.portHandler = PortHandler(self.devicename)

        # Initialize PacketHandler instance
        # Set the protocol version
        # Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
        self.packetHandler = PacketHandler(self.protocol_version)

        # Open port
        if self.portHandler.openPort():
            log.info("Succeeded to open the port")
        else:
            log.error("Failed to open the port")
            log.error("Press any key to terminate...")
            getch()
            quit()

        # Set port baudrate
        if self.portHandler.setBaudRate(self.baudrate):
            log.info("Succeeded to change the baudrate")
        else:
            log.error("Failed to change the baudrate")
            log.error("Press any key to terminate...")
            getch()
            quit()

        log.info("Servo communication started")

    def enable_torque(self):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(
            self.portHandler, self.id, self.addr_torque_enable, self.torque_enable)
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            log.error("%s" % self.packetHandler.getRxPacketError(dxl_error))
        else:
            log.info(f"Servo {self.id} torque enabled")
        self.torque_enabled = True

    def disable_torque(self):
        # Disable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(
            self.portHandler, self.id, self.addr_torque_enable, self.torque_disable)
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            log.error("%s" % self.packetHandler.getRxPacketError(dxl_error))
        else:
            log.info(f"Servo {self.id} torque disabled")
        self.torque_enabled = False

    def norm_degrees(self, x):
        """ Normalize servo from [0, 1] to [min_degrees, max_degrees]. """
        return (x * (self.max_degrees - self.min_degrees)) + self.min_degrees
    
    def norm_position(self, x):
        """ Normalize servo from [min_degrees, max_degrees] to [min_pos, max_pos]. """
        return int(((x / 360.0) * (self.dxl_maximum_position_value - self.dxl_minimum_position_value)) + self.dxl_minimum_position_value)
    
    def move(self, position):
        """ Move servo to position. """

        if not self.torque_enabled:
            self.enable_torque()        
        
        # Normalize goal positions using the minimum and maximum position values.
        dxl_goal_position = self.norm_position(self.norm_degrees(position))

        # Write goal position
        dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(
            self.portHandler, self.id, self.addr_goal_position, dxl_goal_position)
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            log.error("%s" % self.packetHandler.getRxPacketError(dxl_error))
        else:
            log.info(f"Servo {self.id} set goal position to {position}")

        # Move to goal position with timeout
        timeout_start = time.time()
        while time.time() < timeout_start + self.move_timeout:

            # Read present position
            dxl_present_position, dxl_comm_result, dxl_error = self.packetHandler.read4ByteTxRx(
                self.portHandler, self.id, self.addr_present_position)
            if dxl_comm_result != COMM_SUCCESS:
                log.error("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                log.error("%s" % self.packetHandler.getRxPacketError(dxl_error))
            else:
                log.info(f"Servo {self.id} present position {dxl_present_position}")

            if not abs(dxl_goal_position - dxl_present_position) > self.dxl_moving_status_threshold:
                log.info(f"Servo {self.id} reached goal position {dxl_goal_position}")
                break


@contextmanager
def servo_ctx(
    servo_dict: Dict[int, Tuple[int, int]] = {
        # servo 001 - 57600bps MX106 protocol2.0
        1: (100, 150),
        # servo 002 - 57600bps MX106 protocol2.0
        2: (0, 100),
    },
):
    """ Context manager for controlling servos. """
    servos: List[Servo] = []
    for servo_id, (min_degrees, max_degrees) in servo_dict.items():
        servos.append(Servo(servo_id, min_degrees, max_degrees))
    # Connect the first servo
    servos[0].connect()
    # Copy the port handler and packet handler to the other servos
    for servo in servos[1:]:
        servo.portHandler = servos[0].portHandler
        servo.packetHandler = servos[0].packetHandler
    try:
        yield servos
    finally:
        # Disable torque for all servos
        for servo in servos:
            servo.disable_torque()

if __name__ == "__main__":
    with servo_ctx() as servo:
        for servo in servo:
            servo.move(0)
            time.sleep(2)
            servo.move(1)
            time.sleep(2)
            servo.move(0)
            time.sleep(1)