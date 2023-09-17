from dynamixel_sdk import *

# Default parameters
protocol_version = 2.0
baudrate = 57600
devicename = '/dev/ttyUSB0'
addr_torque_enable = 64
addr_goal_position = 116
addr_present_position = 132
torque_enable = 1
torque_disable = 0

# Initialize PortHandler instance
portHandler = PortHandler(devicename)

# Initialize PacketHandler instance
packetHandler = PacketHandler(protocol_version)

# Open port
if not portHandler.openPort():
    print("Failed to open the port")
    exit()

# Set port baudrate
if not portHandler.setBaudRate(baudrate):
    print("Failed to change the baudrate")
    exit()

# Initialize GroupBulkWrite instance
groupBulkWrite = GroupBulkWrite(portHandler, packetHandler)

# Initialize GroupBulkRead instance
groupBulkRead = GroupBulkRead(portHandler, packetHandler)

# Enable torque for all servos and add goal position to the bulk write parameter storage
for dxl_id in range(1, 4):
    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, dxl_id, addr_torque_enable, torque_enable)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    dxl_goal_position = 1000  # Set goal position
    param_goal_position = [DXL_LOBYTE(DXL_LOWORD(dxl_goal_position)), DXL_HIBYTE(DXL_LOWORD(dxl_goal_position)),
                           DXL_LOBYTE(DXL_HIWORD(dxl_goal_position)), DXL_HIBYTE(DXL_HIWORD(dxl_goal_position))]
    groupBulkWrite.addParam(dxl_id, addr_goal_position, 4, param_goal_position)

# Write goal position
dxl_comm_result = groupBulkWrite.txPacket()
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))

# Clear bulk write parameter storage
groupBulkWrite.clearParam()

# Add present position value to the bulk read parameter storage
for dxl_id in range(1, 4):
    dxl_addparam_result = groupBulkRead.addParam(dxl_id, addr_present_position, 4)
    if not dxl_addparam_result:
        print("[ID:%03d] groupBulkRead addparam failed" % dxl_id)
        quit()

# Read present position
dxl_comm_result = groupBulkRead.txRxPacket()
if dxl_comm_result != COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))

# Check if groupsyncread data of Dynamixels are available
for dxl_id in range(1, 4):
    dxl_getdata_result = groupBulkRead.isAvailable(dxl_id, addr_present_position, 4)
    if not dxl_getdata_result:
        print("[ID:%03d] groupBulkRead getdata failed" % dxl_id)
        quit()

# Get present position value
for dxl_id in range(1, 4):
    dxl_present_position = groupBulkRead.getData(dxl_id, addr_present_position, 4)
    print("[ID:%03d] Present Position : %d" % (dxl_id, dxl_present_position))

# Clear bulk read parameter storage
groupBulkRead.clearParam()

# Close port
portHandler.closePort()