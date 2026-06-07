import os

import yaml
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")

    moveit_config = MoveItConfigsBuilder(
        "my_ur", package_name="my_ur_moveit_config"
    ).to_moveit_configs()

    move_group_ld = generate_move_group_launch(moveit_config)

    rviz_config = PathJoinSubstitution(
        [FindPackageShare("my_ur_bringup"), "rviz", "rviz_config.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        parameters=[
            {"use_sim_time": use_sim_time},
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    _servo_yaml_path = os.path.join(
        get_package_share_directory("my_ur_moveit_config"), "config", "ur_servo.yaml"
    )
    with open(_servo_yaml_path, encoding="utf-8") as _f:
        servo_params = {"moveit_servo": yaml.safe_load(_f)}
    launch_servo = LaunchConfiguration("launch_servo")

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node",
        name="servo_node",
        output="screen",
        parameters=[
            servo_params,
            {"use_sim_time": use_sim_time},
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        condition=IfCondition(launch_servo),
    )

    ld = LaunchDescription(move_group_ld.entities)
    ld.add_action(DeclareLaunchArgument("use_sim_time", default_value="false"))
    ld.add_action(DeclareLaunchArgument("launch_servo", default_value="false"))
    ld.add_action(rviz_node)
    ld.add_action(servo_node)
    return ld
