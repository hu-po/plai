import logging
from dynamixel_sdk import PortHandler, PacketHandler, GroupBulkWrite, GroupBulkRead, COMM_SUCCESS, DXL_LOBYTE, DXL_LOWORD, DXL_HIBYTE, DXL_HIWORD

log = logging.getLogger('plai')

class Robot:
    def __init__(self, dxl_ids, protocol_version=2.0, baudrate=57600, device_name='/dev/ttyUSB0'):
        self.dxl_ids = dxl_ids  # List of DYNAMIXEL IDs to control
        self.protocol_version = protocol_version  # DYNAMIXEL Protocol version (1.0 or 2.0)
        self.baudrate = baudrate  # Baudrate for DYNAMIXEL communication
        self.device_name = device_name  # Name of the device (port) where DYNAMIXELs are connected
        self.addr_torque_enable = 64  # Address for Torque Enable control table in DYNAMIXEL
        self.addr_goal_position = 116  # Address for Goal Position control table in DYNAMIXEL
        self.addr_present_position = 132  # Address for Present Position control table in DYNAMIXEL
        self.torque_enable = 1  # Value to enable the torque
        self.torque_disable = 0  # Value to disable the torque

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

    def move(self, goal_positions):
        # Enable torque for all servos and add goal position to the bulk write parameter storage
        for dxl_id, goal_position in zip(self.dxl_ids, goal_positions):
            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(self.port_handler, dxl_id, self.addr_torque_enable, self.torque_enable)
            if dxl_comm_result != COMM_SUCCESS:
                log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                log.error("%s" % self.packet_handler.getRxPacketError(dxl_error))

            param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_position)), DXL_HIBYTE(DXL_LOWORD(goal_position)),
                                   DXL_LOBYTE(DXL_HIWORD(goal_position)), DXL_HIBYTE(DXL_HIWORD(goal_position))]
            self.group_bulk_write.addParam(dxl_id, self.addr_goal_position, 4, param_goal_position)

        # Write goal position
        dxl_comm_result = self.group_bulk_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Clear bulk write parameter storage
        self.group_bulk_write.clearParam()

    def get_position(self):
        # Add present position value to the bulk read parameter storage
        for dxl_id in self.dxl_ids:
            dxl_addparam_result = self.group_bulk_read.addParam(dxl_id, self.addr_present_position, 4)
            if not dxl_addparam_result:
                log.error("[ID:%03d] groupBulkRead addparam failed" % dxl_id)
                quit()

        # Read present position
        dxl_comm_result = self.group_bulk_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            log.error("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Get present position value
        positions = []
        for dxl_id in self.dxl_ids:
            dxl_present_position = self.group_bulk_read.getData(dxl_id, self.addr_present_position, 4)
            positions.append(dxl_present_position)

        # Clear bulk read parameter storage
        self.group_bulk_read.clearParam()

        return positions

    def close(self):
        # Close port
        self.port_handler.closePort()

if __name__ == '__main__':
    # Set robot parameters
    dxl_ids = [1, 2, 3]
    protocol_version = 2.0
    baudrate = 57600
    device_name = '/dev/ttyUSB0'

    # Initialize robot
    robot = Robot(dxl_ids, protocol_version, baudrate, device_name)

    # Set goal positions
    goal_positions_list = [[0, 0, 0], [100, 200, 300], [500, 400, 300]]

    for goal_positions in goal_positions_list:
        # Move robot
        robot.move(goal_positions)
        time.sleep(2)

        # Get present position
        positions = robot.get_position()
        log.info(positions)

    # Close robot
    robot.close()

