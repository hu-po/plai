from dynamixel_sdk import PortHandler, PacketHandler, GroupBulkWrite, GroupBulkRead, COMM_SUCCESS, DXL_LOBYTE, DXL_LOWORD, DXL_HIBYTE, DXL_HIWORD

class Robot:
    def __init__(self, dxl_ids, protocol_version=2.0, baudrate=57600, device_name='/dev/ttyUSB0'):
        self.dxl_ids = dxl_ids
        self.protocol_version = protocol_version
        self.baudrate = baudrate
        self.device_name = device_name
        self.addr_torque_enable = 64
        self.addr_goal_position = 116
        self.addr_present_position = 132
        self.torque_enable = 1
        self.torque_disable = 0

        # Initialize PortHandler instance
        self.port_handler = PortHandler(self.device_name)

        # Initialize PacketHandler instance
        self.packet_handler = PacketHandler(self.protocol_version)

        # Open port
        if not self.port_handler.openPort():
            print("Failed to open the port")
            exit()

        # Set port baudrate
        if not self.port_handler.setBaudRate(self.baudrate):
            print("Failed to change the baudrate")
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
                print("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                print("%s" % self.packet_handler.getRxPacketError(dxl_error))

            param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_position)), DXL_HIBYTE(DXL_LOWORD(goal_position)),
                                   DXL_LOBYTE(DXL_HIWORD(goal_position)), DXL_HIBYTE(DXL_HIWORD(goal_position))]
            self.group_bulk_write.addParam(dxl_id, self.addr_goal_position, 4, param_goal_position)

        # Write goal position
        dxl_comm_result = self.group_bulk_write.txPacket()
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

        # Clear bulk write parameter storage
        self.group_bulk_write.clearParam()

    def get_position(self):
        # Add present position value to the bulk read parameter storage
        for dxl_id in self.dxl_ids:
            dxl_addparam_result = self.group_bulk_read.addParam(dxl_id, self.addr_present_position, 4)
            if not dxl_addparam_result:
                print("[ID:%03d] groupBulkRead addparam failed" % dxl_id)
                quit()

        # Read present position
        dxl_comm_result = self.group_bulk_read.txRxPacket()
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packet_handler.getTxRxResult(dxl_comm_result))

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

    # Set goal position
    goal_positions = [0, 0, 0]

    # Move robot
    robot.move(goal_positions)

    # Get present position
    positions = robot.get_position()
    print(positions)

    # Close robot
    robot.close()
