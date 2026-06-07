from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
	ur_type = LaunchConfiguration("ur_type")
	description_file = LaunchConfiguration("description_file")
	launch_servo = LaunchConfiguration("launch_servo")

	declared_arguments = []
	declared_arguments.append(
		DeclareLaunchArgument("ur_type", default_value="ur5")
	)
	declared_arguments.append(
		DeclareLaunchArgument("launch_servo", default_value="false")
	)
	declared_arguments.append(
		DeclareLaunchArgument(
			"description_file",
			default_value=PathJoinSubstitution(
				[
					FindPackageShare("my_ur_bringup"),
					"urdf",
					"my_ur_controlled_simulator.urdf.xacro",
				]
			),
		)
	)
	declared_arguments.append(
		DeclareLaunchArgument(
			"use_mock_hardware",
			default_value="true",
			description="Start robot with mock hardware mirroring command to its states.",
		)
	)

	ur_sim_control_launch = IncludeLaunchDescription(
		PythonLaunchDescriptionSource(
			PathJoinSubstitution(
				[
					FindPackageShare("ur_simulation_gz"),
					"launch",
					"ur_sim_control.launch.py",
				]
			)
		),
		launch_arguments={
			"ur_type": ur_type,
			"description_file": description_file,
			"launch_rviz": "false",
		}.items(),
	)

	movegroup_launch = IncludeLaunchDescription(
		PythonLaunchDescriptionSource(
			PathJoinSubstitution(
				[
					FindPackageShare("my_ur_bringup"),
					"launch",
					"movegroup.launch.py",
				]
			)
		),
		launch_arguments={
			"use_sim_time": "true",
			"launch_servo": launch_servo,
		}.items(),
	)

	return LaunchDescription(declared_arguments + [ur_sim_control_launch, movegroup_launch])
