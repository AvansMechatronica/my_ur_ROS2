from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch

from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
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
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    ld = LaunchDescription(move_group_ld.entities)
    ld.add_action(rviz_node)
    return ld
