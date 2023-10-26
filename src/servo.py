import logging
import time
import datetime
from datetime import timedelta
from dataclasses import dataclass
from typing import List, Union, Tuple

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


@dataclass
class Servo:
    id: int # dynamixel id for servo
    name: str # name of servo for llm use
    range: Tuple[int, int] # (min, max) position values for servos (0, 4095)
    desc: str # description of servo for llm use

# log.info("Using robot 0.0.1 created on 26.09.2023")
# DEFAULT_SERVOS = [
#     Servo(1, "hip", (1676, 2293),"swings the robot horizontally from left to right, yaw"),
#     Servo(2, "toy", (1525, 2453),"tilts the toy arm up and down, pitch"),
#     Servo(3, "cam", (1816, 3007),"tilts the camera up and down, pitch"),
# ]

log.info("Using robot 0.1.0 created on 26.10.2023")
DEFAULT_SERVOS = [
    Servo(1, "roll", (1761, 2499), "rolls the neck left and right rotating the view"),
    Servo(2, "tilt", (979, 2223), "tilts the head up and down vertically"),
    Servo(3, "pan", (988, 3007), "pans the head side to side horizontally")
]

class Servos:
    def __init__(
        self,
        servos: List[Servo] = DEFAULT_SERVOS,
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
        self.protocol_version = protocol_version  # DYNAMIXEL Protocol version (1.0 or 2.0)
        self.baudrate = baudrate  # Baudrate for DYNAMIXEL communication
        self.device_name = device_name  # Name of the device (port) where DYNAMIXELs are connected
        self.addr_torque_enable = addr_torque_enable  # Address for Torque Enable control table in DYNAMIXEL
        self.addr_goal_position = addr_goal_position  # Address for Goal Position control table in DYNAMIXEL
        self.addr_present_position = addr_present_position  # Address for Present Position control table in DYNAMIXEL
        self.torque_enable = torque_enable  # Value to enable the torque
        self.torque_disable = torque_disable  # Value to disable the torque

        # Initialize PortHandler instance
        self.port_handler = PortHandler(self.device_name)

        # Initialize PacketHandler instance
        self.packet_handler = PacketHandler(self.protocol_version)

        # Open port
        if not self.port_handler.openPort():
            log.error("Failed to open the port")
            exit()

        # Set port baudrate
        if not self.port_handler.setBaudRate(self.baudrate):
            log.error("Failed to change the baudrate")
            exit()

        # Initialize GroupBulkWrite instance
        self.group_bulk_write = GroupBulkWrite(self.port_handler, self.packet_handler)

        # Initialize GroupBulkRead instance
        self.group_bulk_read = GroupBulkRead(self.port_handler, self.packet_handler)

    def move(self, *args: int) -> None:
        # The name of the function matters for LLMs, so this
        # simply maps move to write_pos
        self.write_pos(*args)

    def move_to(
        self,
        *args: int,
        epsilon: int = 10,
        time_limit: timedelta = timedelta(seconds=1.0),
    ) -> None:
        self.move(*args)
        start_time = time.time()
        while True:
            if time.time() - start_time > time_limit.total_seconds():
                log.error(f"Timeout exceeded on MOVE_TO: {time_limit}s")
                break
            positions = self.read_pos()
            log.debug(f"Servo positions: {positions}")
            # cumulative error
            error = sum(abs(positions[i] - args[i]) for i in range(len(args)))
            if error < epsilon:
                log.info(f"MOVE_TO complete: {positions}")
                break

    def write_pos(self, *args: int) -> None:
        if len(args) != len(self.servos):
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
            log.debug(f"WRITE position to servo {dxl_id}: {pos} or {self.position_to_degrees(pos)}deg")

        # Write goal position
        dxl_comm_result = self.group_bulk_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Clear bulk write parameter storage
        self.group_bulk_write.clearParam()

    def read_pos(self) -> List[int]:
        # Add present position value to the bulk read parameter storage
        for i in range(len(self.servos)):
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
        for i in range(len(self.servos)):
            dxl_id = self.servos[i].id
            dxl_present_position = self.group_bulk_read.getData(
                dxl_id, self.addr_present_position, 4
            )
            positions.append(dxl_present_position)

        # Clear bulk read parameter storage
        self.group_bulk_read.clearParam()

        return positions

    def close(self) -> None:
        # Close port
        self.port_handler.closePort()

    @staticmethod
    def degrees_to_position(
        degrees: Union[int, List[int]], max_position: int = 4095, max_degrees: int = 360
    ) -> Union[int, List[int]]:
        """
        Convert degrees to position value.
        If degrees is a list, return a list of positions.
        """
        if isinstance(degrees, list):
            positions = [(degree / max_degrees) * max_position for degree in degrees]
            return [int(position) for position in positions]
        else:
            position = (degrees / max_degrees) * max_position
            return int(position)

    @staticmethod
    def position_to_degrees(
        position: Union[int, List[int]],
        max_position: int = 4095,
        max_degrees: int = 360,
    ) -> Union[float, List[float]]:
        """
        Convert position value to degrees.
        If position is a list, return a list of degrees.
        """
        if isinstance(position, list):
            degrees = [(pos / max_position) * max_degrees for pos in position]
            return degrees
        else:
            degrees = (position / max_position) * max_degrees
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
    robot = Servos()

    # Initialize lists to store commanded and true positions
    commanded_positions = []
    true_positions = []
    commanded_timestamps = []
    true_timestamps = []

    # Read positions for tests
    def read():
        _position = robot.read_pos()
        true_positions.append(_position)
        true_timestamps.append(datetime.datetime.now())
        _degrees = robot.position_to_degrees(_position)
        log.debug(f"READ position: {_position} or {_degrees}")

    log.debug(f"Testing write_pos and read_pos")
    _position: List[int] = [
        int((robot.servos[0].range[0] + robot.servos[0].range[1]) / 2),
        int((robot.servos[1].range[0] + robot.servos[1].range[1]) / 2),
        int((robot.servos[2].range[0] + robot.servos[2].range[1]) / 2),
    ]
    _degrees: List[int] = robot.position_to_degrees(_position)
    log.debug(f"WRITE to: {_position} or {_degrees}")
    read()
    robot.write_pos(*_position)
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
