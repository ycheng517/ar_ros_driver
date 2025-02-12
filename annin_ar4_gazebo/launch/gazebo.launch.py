# Copyright (c) 2021 Stogl Robotics Consulting UG (haftungsbeschränkt)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the {copyright_holder} nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Denis Stogl
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch.substitutions import FindExecutable
from launch.substitutions import PathJoinSubstitution
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ar_model_arg = DeclareLaunchArgument("ar_model",
                                         default_value="mk3",
                                         choices=["mk1", "mk2", "mk3"],
                                         description="Model of AR4")
    namespace_arg = DeclareLaunchArgument("namespace",
                                          default_value="/",
                                          description="Namespace of AR4")

    ar_model_config = LaunchConfiguration("ar_model")
    namespace_config = LaunchConfiguration("namespace")

    initial_joint_controllers = PathJoinSubstitution(
        [FindPackageShare("annin_ar4_driver"), "config", "controllers.yaml"])

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("annin_ar4_description"), "urdf",
            "ar_gazebo.urdf.xacro"
        ]),
        " ",
        "ar_model:=",
        ar_model_config,
        " ",
        "namespace:=",
        namespace_config,
        " ",
        "simulation_controllers:=",
        initial_joint_controllers,
    ])
    robot_description = {"robot_description": robot_description_content}

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace=namespace_config,
        output="both",
        parameters=[robot_description],
        remappings=[('/tf', PathJoinSubstitution([namespace_config, 'tf'])),
                    ('/tf_static',
                     PathJoinSubstitution([namespace_config, 'tf_static']))])

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "-c",
            PathJoinSubstitution([namespace_config, "controller_manager"]),
        ],
        namespace=namespace_config)

    # There may be other controllers of the joints, but this is the initially-started one
    initial_joint_controller_spawner_started = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_trajectory_controller",
            "--param-file",
            initial_joint_controllers,
            "-c",
            PathJoinSubstitution([namespace_config, "controller_manager"]),
        ],
    )

    gripper_joint_controller_spawner_started = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "gripper_controller",
            "-c",
            PathJoinSubstitution([namespace_config, "controller_manager"]),
            "--param-file",
            initial_joint_controllers,
        ],
    )

    # Gazebo nodes
    world = os.path.join(get_package_share_directory('annin_ar4_gazebo'),
                         'worlds', 'empty.world')

    # Bridge
    gazebo_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=["/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"],
        output='screen',
        namespace=namespace_config)

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ros_gz_sim"), "/launch", "/gz_sim.launch.py"]),
        launch_arguments={
            'gz_args':
            f'-r -v 4 --physics-engine gz-physics-bullet-featherstone-plugin {world}',
            'on_exit_shutdown': 'True'
        }.items())

    # Spawn robot
    gazebo_spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", ar_model_config, "-topic",
            PathJoinSubstitution([namespace_config, "robot_description"])
        ],
        output="screen",
        namespace=namespace_config,
    )

    return LaunchDescription([
        ar_model_arg,
        namespace_arg,
        gazebo_bridge,
        gazebo,
        gazebo_spawn_robot,
        robot_state_publisher_node,
        joint_state_broadcaster_spawner,
        initial_joint_controller_spawner_started,
        gripper_joint_controller_spawner_started,
    ])
