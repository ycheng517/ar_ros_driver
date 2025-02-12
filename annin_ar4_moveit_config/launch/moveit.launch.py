# Copyright (c) 2021 PickNik, Inc.
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
import tempfile
import yaml

from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from launch.substitution import Substitution
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)


def load_yaml(package_name, file_name):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_name)
    with open(absolute_file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


class RvizConfigSubstitution(Substitution):
    """Substitution to modify the RViz config file to include the namespace."""

    def __init__(self, file_path: Substitution, namespace: Substitution):
        super().__init__()
        self._file_path = file_path
        self._namespace = namespace

    def perform(self, context):
        # Evaluate the file path and namespace substitutions
        file_path_val = self._file_path.perform(context)
        namespace_val = self._namespace.perform(context)

        # If the namespace is "/" or empty, no substitution is necessary.
        if namespace_val in ["/", ""]:
            return file_path_val

        with open(file_path_val, "r") as f:
            content = f.read()

        content = content.replace('Move Group Namespace: ""',
                                  f'Move Group Namespace: {namespace_val}')

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".rviz")
        temp_file.write(content.encode("utf-8"))
        temp_file.close()
        return temp_file.name


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    include_gripper = LaunchConfiguration("include_gripper")
    ar_model_config = LaunchConfiguration("ar_model")
    rviz_config_file = LaunchConfiguration("rviz_config_file")
    namespace_config = LaunchConfiguration("namespace")

    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="False",
            description="Make MoveIt use simulation time. This is needed "+\
                "for trajectory planing in simulation.",
        ))
    declared_arguments.append(
        DeclareLaunchArgument(
            "include_gripper",
            default_value="True",
            description="Run the servo gripper",
            choices=["True", "False"],
        ))
    rviz_config_file_default = PathJoinSubstitution(
        [FindPackageShare("annin_ar4_moveit_config"), "rviz", "moveit.rviz"])
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config_file",
            default_value=rviz_config_file_default,
            description="Full path to the RViz configuration file to use",
        ))
    declared_arguments.append(
        DeclareLaunchArgument("ar_model",
                              default_value="mk3",
                              choices=["mk1", "mk2", "mk3"],
                              description="Model of AR4"))
    declared_arguments.append(
        DeclareLaunchArgument("namespace",
                              default_value="/",
                              description="Namespace of AR4"))

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("annin_ar4_description"), "urdf", "ar.urdf.xacro"
        ]),
        " ",
        "ar_model:=",
        ar_model_config,
        " ",
        "include_gripper:=",
        include_gripper,
    ])
    robot_description = {"robot_description": robot_description_content}

    # MoveIt Configuration
    robot_description_semantic_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([
            FindPackageShare("annin_ar4_moveit_config"), "srdf",
            "ar.srdf.xacro"
        ]),
        " ",
        "name:=",
        ar_model_config,
        " ",
        "include_gripper:=",
        include_gripper,
    ])
    robot_description_semantic = {
        "robot_description_semantic": robot_description_semantic_content
    }

    robot_description_kinematics_content = load_yaml(
        "annin_ar4_moveit_config",
        os.path.join("config", "kinematics.yaml"),
    )
    robot_description_kinematics = {
        "robot_description_kinematics": robot_description_kinematics_content
    }

    robot_description_planning = {
        "robot_description_planning":
        load_yaml(
            "annin_ar4_moveit_config",
            os.path.join("config", "joint_limits.yaml"),
        )
    }

    # Planning Configuration
    ompl_planning_yaml = load_yaml("annin_ar4_moveit_config",
                                   "config/ompl_planning.yaml")
    pilz_planning_yaml = load_yaml("annin_ar4_moveit_config",
                                   "config/pilz_planning.yaml")
    planning_pipeline_config = {
        "default_planning_pipeline": "ompl",
        "planning_pipelines": ["ompl", "pilz"],
        "ompl": ompl_planning_yaml,
        "pilz": pilz_planning_yaml,
    }

    # Trajectory Execution Configuration
    controllers_yaml = load_yaml("annin_ar4_moveit_config",
                                 "config/controllers.yaml")

    moveit_controllers = {
        "moveit_simple_controller_manager":
        controllers_yaml,
        "moveit_controller_manager":
        "moveit_simple_controller_manager/MoveItSimpleControllerManager",
    }

    trajectory_execution = {
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 1.2,
        "trajectory_execution.allowed_goal_duration_margin": 0.5,
        "trajectory_execution.allowed_start_tolerance": 0.01,
    }

    planning_scene_monitor_parameters = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        # Added due to https://github.com/moveit/moveit2_tutorials/issues/528
        "publish_robot_description_semantic": True,
    }

    # Starts Pilz Industrial Motion Planner MoveGroupSequenceAction and MoveGroupSequenceService servers
    move_group_capabilities = {
        "capabilities":
        "pilz_industrial_motion_planner/MoveGroupSequenceAction pilz_industrial_motion_planner/MoveGroupSequenceService"
    }

    # Start the actual move_group node/action server
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            planning_pipeline_config,
            trajectory_execution,
            moveit_controllers,
            planning_scene_monitor_parameters,
            move_group_capabilities,
            {
                "use_sim_time": use_sim_time
            },
        ],
        namespace=namespace_config,
    )

    # rviz with moveit configuration
    rviz_config_with_namespace = RvizConfigSubstitution(
        rviz_config_file, namespace_config)
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="log",
        arguments=["-d", rviz_config_with_namespace],
        parameters=[
            robot_description,
            robot_description_semantic,
            planning_pipeline_config,
            robot_description_kinematics,
            {
                "use_sim_time": use_sim_time
            },
        ],
        namespace=namespace_config,
    )
    nodes_to_start = [move_group_node, rviz_node]
    return LaunchDescription(declared_arguments + nodes_to_start)
