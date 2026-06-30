import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    package_share = get_package_share_directory("my_ur_moveit_config")
    moveit_config = MoveItConfigsBuilder(
        "my_ur", package_name="my_ur_moveit_config"
    ).to_moveit_configs()

    servo_yaml_path = os.path.join(package_share, "config", "ur_servo.yaml")
    with open(servo_yaml_path, encoding="utf-8") as servo_yaml_file:
        servo_params = {"moveit_servo": yaml.safe_load(servo_yaml_file)}

    launch_rviz = LaunchConfiguration("launch_rviz")

    rsp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(package_share, "launch", "rsp.launch.py"))
    )
    static_tf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, "launch", "static_virtual_joint_tfs.launch.py")
        )
    )
    move_group_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, "launch", "move_group.launch.py")
        )
    )
    rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(package_share, "launch", "moveit_rviz.launch.py")
        ),
        condition=IfCondition(launch_rviz),
    )

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node",
        name="servo_node",
        output="screen",
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            rsp_launch,
            static_tf_launch,
            move_group_launch,
            rviz_launch,
            servo_node,
        ]
    )