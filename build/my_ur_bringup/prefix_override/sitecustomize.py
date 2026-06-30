import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/student2/my_ur_ws/src/my_ur_ROS2/install/my_ur_bringup'
