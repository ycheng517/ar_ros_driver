#pragma once

#include <boost/asio.hpp>
#include <rclcpp/rclcpp.hpp>
#include <string>
#include <unordered_map>
#include <vector>

#include "math.h"
#include "time.h"

namespace ar_gripper_hardware_interface {

class ArduinoNanoDriver {
 public:
  bool init(std::string port, int baudrate);
  void update(std::vector<double>& pos_commands,
              std::vector<double>& joint_states);
  void getJointPositions(std::vector<double>& joint_positions);
  std::string sendCommand(std::string outMsg);

  ArduinoNanoDriver();

 private:
  bool initialised_;
  std::string version_;
  boost::asio::io_service io_service_;
  boost::asio::serial_port serial_port_;
  rclcpp::Logger logger_ = rclcpp::get_logger("arduino_nano_driver");

  double gripper_position_ = 0.0;
  double gripper_velocity_ = 0.0;
  double gripper_position_command_ = 0.0;

  bool transmit(std::string outMsg, std::string& err);
  void receive(std::string& inMsg);

  bool checkInit(std::string msg);
};

}  // namespace ar_gripper_hardware_interface
