from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetParameter


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "my_ur", package_name="my_ur_moveit_config"
    ).to_moveit_configs()

    base_ld = generate_move_group_launch(moveit_config)

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument("use_sim_time", default_value="false"))
    ld.add_action(
        SetParameter(name="use_sim_time", value=LaunchConfiguration("use_sim_time"))
    )

    for entity in base_ld.entities:
        ld.add_action(entity)

    return ld
