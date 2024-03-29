import logging
import time
import datetime
from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, List, Union, Tuple

from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    GroupBulkWrite,
    GroupBulkRead,
    COMM_SUCCESS,
    DXL_LOBYTE,
    DXL_LOWORD,
    DXL_HIBYTE,
    DXL_HIWORD,
)

log = logging.getLogger(__name__)


from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos (0, 4095)
    desc: str # description of servo for llm use

SERVOS: List[Servo] = [
    Servo(1, "roll", (1761, 2499), "rolls the neck left and right rotating the view, roll"),
    Servo(2, "tilt", (979, 2223), "tilts the head up and down vertically, pitch"),
    Servo(3, "pan", (988, 3007), "pans the head side to side horizontally, yaw")
]

@dataclass
class Pose:
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use

POSES: Dict[str, Pose] = {
    'home': Pose([180, 211, 180], "home position or look up"),
    'forward': Pose([180, 140, 180], "look ahead, facing forward"),
    'tilt left': Pose([215, 130, 151], "looking forward, head tilted right"),
    'tilt right': Pose([145, 130, 209], "looking forward, head tilted left"),
    'down': Pose([180, 94, 180], "looking down, facing forward")
}

ROBOT_DESCRIPTION: str = """
You are an llm control unit for a robot arm.
This arm has with 3 servos forming a kinematic chain.
The Servo dataclass holds information for each servo:

@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos (0, 4095)
    desc: str # description of servo for llm use

The robot arm can be put into different poses.
The Pose dataclass holds information for each pose:

@dataclass
class Pose:
    angles: List[int] # list of int angles in degrees (0, 360)
    desc: str # description of position for llm use

The robot arm you currently control has the following specifications
SERVOS: List[Servo] = [
    Servo(1, "roll", (1761, 2499), "rolls the neck left and right rotating the view, roll"),
    Servo(2, "tilt", (979, 2223), "tilts the head up and down vertically, pitch"),
    Servo(3, "pan", (988, 3007), "pans the head side to side horizontally, yaw")
]
POSES: Dict[str : Pose] = {
    'home' : Pose([180, 211, 180], "home position or look up"),
    'forward' : Pose([180, 140, 180], "look ahead, facing forward"),
    'tilt left' : Pose([215, 130, 151], "looking forward, head tilted right"),
    'tilt right' : Pose([145, 130, 209], "looking forward, head tilted left"),
    'down' : Pose([180, 94, 180], "looking down, facing forward")
}
"""

MOVE_DESCRIPTION: str = """
Choose one of the valid poses given a user description.
The name of the pose must match the name of one of the pose in the POSES dict.
Here are some examples of user descriptions and correct pose choices:
"go to the home position" -> "home"
"face the forward direction" -> "forward"
"look down" -> "down"
The user will now describe a pose, return the name of one of the valid poses.
"""

class Robot:
    def __init__(
        self,
        servos: List[Servo] = SERVOS,
        poses: Dict[str, Pose] = POSES,
        desc: str = ROBOT_DESCRIPTION,
        move_desc: str = MOVE_DESCRIPTION,
        protocol_version: float = 2.0,
        baudrate: int = 57600,
        device_name: str = "/dev/ttyUSB0",
        addr_torque_enable: int = 64,
        addr_goal_position: int = 116,
        addr_present_position: int = 132,
        torque_enable: int = 1,
        torque_disable: int = 0,
    ):
        self.servos = servos  # List of Servo objects to control
        for servo in self.servos:
            log.debug("---- Initialize servo ----")
            log.debug(f"servo: {servo.name}")
            log.debug(f"id: {servo.id}")
            log.debug(f"range: {servo.range}")
            log.debug(f"description: {servo.desc}")
        self.num_servos: int = len(self.servos)  # Number of servos to control
        self.poses = poses # Dict of Pose objects to control
        self.desc = desc # Description of robot for llm use
        self.move_desc = move_desc # Description of move for llm use

        # Dynamixel communication parameters
        self.protocol_version = protocol_version  # DYNAMIXEL Protocol version (1.0 or 2.0)
        self.baudrate = baudrate  # Baudrate for DYNAMIXEL communication
        self.device_name = device_name  # Name of the device (port) where DYNAMIXELs are connected
        self.addr_torque_enable = addr_torque_enable  # Address for Torque Enable control table in DYNAMIXEL
        self.addr_goal_position = addr_goal_position  # Address for Goal Position control table in DYNAMIXEL
        self.addr_present_position = addr_present_position  # Address for Present Position control table in DYNAMIXEL
        self.torque_enable = torque_enable  # Value to enable the torque
        self.torque_disable = torque_disable  # Value to disable the torque

        # Initialize DYNAMIXEL communication
        self.port_handler = PortHandler(self.device_name)
        self.packet_handler = PacketHandler(self.protocol_version)
        if not self.port_handler.openPort():
            log.error("Failed to open the port")
            exit()
        if not self.port_handler.setBaudRate(self.baudrate):
            log.error("Failed to change the baudrate")
            exit()
        self.group_bulk_write = GroupBulkWrite(self.port_handler, self.packet_handler)
        self.group_bulk_read = GroupBulkRead(self.port_handler, self.packet_handler)

    def move_with_prompt(self,
        position_str: int = "home",
        llm_func: callable = None,
    ) -> str:
        desired_pose = llm_func(
                max_tokens=8,
                messages=[
                    {"role": "system", "content": self.desc + self.move_desc},
                    {"role": "user", "content": position_str},
                ]
        )
        log.debug(f"Desired pose: {desired_pose}")
        if desired_pose in self.poses:
            log.debug(f"Moving to pose: {desired_pose}")
            return self.move_to(*self.poses[desired_pose].angles)
        else:
            return "Invalid pose."

    def move(self, *args: int) -> List[int]:
        # The name of the function matters for LLMs, so this
        # simply maps move to write_pos
        self._write_pos(*self.units_to_degrees(*args))
        return self.degrees_to_units(self._read_pos())

    def move_to(
        self,
        *args: int,
        epsilon: int = 10, # degrees
        timeout: timedelta = timedelta(seconds=1.0), #timeout
    ) -> str:
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            positions = self.move(*args)
            if epsilon > sum(abs(positions[i] - args[i]) for i in range(len(args))):
                return f"MOVE_TO succeeded in {elapsed_time} seconds. Robot at position {positions} degrees."
            if elapsed_time > timeout.total_seconds():
                return f"MOVE_TO to timed out after {elapsed_time} seconds. Robot at position {positions} degrees."

    def _write_pos(self, *args: int) -> str:
        if len(args) != self.num_servos:
            raise ValueError("Number of positions does not match the number of servos.")
        # Enable torque for all servos and add goal position to the bulk write parameter storage
        for i, pos in enumerate(args):
            dxl_id = self.servos[i].id
            clipped = min(max(pos, self.servos[i].range[0]), self.servos[i].range[1])

            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, self.addr_torque_enable, self.torque_enable
            )
            if dxl_comm_result != COMM_SUCCESS:
                log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                log.error("%s" % self.packet_handler.getRxPacketError(dxl_error))

            self.group_bulk_write.addParam(
                dxl_id, self.addr_goal_position, 4, [
                DXL_LOBYTE(DXL_LOWORD(clipped)),
                DXL_HIBYTE(DXL_LOWORD(clipped)),
                DXL_LOBYTE(DXL_HIWORD(clipped)),
                DXL_HIBYTE(DXL_HIWORD(clipped)),
            ])
            return "WRITE position to servo {dxl_id}: {pos} or {self.units_to_degrees(pos)}deg"

        # Write goal position
        dxl_comm_result = self.group_bulk_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Clear bulk write parameter storage
        self.group_bulk_write.clearParam()

    def _read_pos(self) -> List[int]:
        # Add present position value to the bulk read parameter storage
        for i in range(self.num_servos):
            dxl_id = self.servos[i].id
            dxl_addparam_result = self.group_bulk_read.addParam(
                dxl_id, self.addr_present_position, 4
            )
            if not dxl_addparam_result:
                log.error("[ID:%03d] groupBulkRead addparam failed" % dxl_id)
                quit()

        # Read present position
        dxl_comm_result = self.group_bulk_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Get present position value
        positions = []
        for i in range(self.num_servos):
            dxl_id = self.servos[i].id
            dxl_present_position = self.group_bulk_read.getData(
                dxl_id, self.addr_present_position, 4
            )
            positions.append(dxl_present_position)

        # Clear bulk read parameter storage
        self.group_bulk_read.clearParam()

        return positions

    def close(self) -> None:
        self.port_handler.closePort()

    def __del__(self, *args, **kwargs) -> None:
        self.close()

    @staticmethod
    def degrees_to_units(
        degrees: Union[int, List[int]],
        conversion_factor: float = 11.375
    ) -> Union[int, List[int]]:
        if isinstance(degrees, list):
            positions = [int(degree * conversion_factor) for degree in degrees]
            return positions
        else:
            position = int(degrees * conversion_factor)
            return position

    @staticmethod
    def units_to_degrees(
        position: Union[int, List[int]],
        conversion_factor: float = 0.088
    ) -> Union[float, List[float]]:
        if isinstance(position, list):
            degrees = [float(pos) * conversion_factor for pos in position]
            return degrees
        else:
            degrees = float(position) * conversion_factor
            return degrees


def test_servos(
    matplotlib: bool = True,
) -> None:
    """
    Test the Servo module.

    """
    # Set logging level
    logging.basicConfig(level=logging.DEBUG)

    # Initialize robot
    robot = Robot()

    # Initialize lists to store commanded and true positions
    commanded_positions = []
    true_positions = []
    commanded_timestamps = []
    true_timestamps = []

    # Read positions for tests
    def read():
        _position = robot._read_pos()
        true_positions.append(_position)
        true_timestamps.append(datetime.datetime.now())
        _degrees = robot.units_to_degrees(_position)
        log.debug(f"READ position: {_position} or {_degrees}")

    log.debug(f"Testing write_pos and read_pos")
    _position: List[int] = [
        int((robot.servos[0].range[0] + robot.servos[0].range[1]) / 2),
        int((robot.servos[1].range[0] + robot.servos[1].range[1]) / 2),
        int((robot.servos[2].range[0] + robot.servos[2].range[1]) / 2),
    ]
    _degrees: List[int] = robot.units_to_degrees(_position)
    log.debug(f"WRITE to: {_position} or {_degrees}")
    read()
    robot._write_pos(*_position)
    read()
    commanded_positions.append(_position)
    commanded_timestamps.append(datetime.datetime.now())
    time.sleep(0.1)
    read()

    log.debug(f"Testing move")
    for step in [
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
    ]:
        read()
        robot.move(*step)
        commanded_positions.append(step)
        commanded_timestamps.append(datetime.datetime.now())
        read()
        time.sleep(1)
        read()

    log.debug(f"Testing move_to")
    for step in [
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
        [robot.servos[0].range[0], robot.servos[1].range[0], robot.servos[2].range[0]],
        [robot.servos[0].range[1], robot.servos[1].range[1], robot.servos[2].range[1]],
    ]:
        read()
        robot.move_to(*step)
        commanded_positions.append(step)
        commanded_timestamps.append(datetime.datetime.now())
        read()
        read()
        time.sleep(1)
        read()

    # Close robot
    robot.close()

    # Plot commanded and true positions
    if matplotlib:
        import matplotlib.pyplot as plt

        plt.figure()
        plt.plot(commanded_timestamps, commanded_positions, label="Commanded Positions")
        plt.plot(true_timestamps, true_positions, label="True Positions")
        plt.xlabel("Time")
        plt.ylabel("Positions")
        plt.legend()
        plt.savefig("output.png")


if __name__ == "__main__":
    test_servos()
