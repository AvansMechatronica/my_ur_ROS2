#!/usr/bin/env python3
"""PyQt5 control panel for the UR ros2_control controllers (topics and services)."""

import signal
import sys

from builtin_interfaces.msg import Duration
from control_msgs.msg import SpeedScalingFactor
from geometry_msgs.msg import PoseStamped, WrenchStamped
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from std_msgs.msg import Bool, Float64, String
from std_srvs.srv import Trigger
from ur_dashboard_msgs.msg import RobotMode, SafetyMode
from ur_msgs.msg import IOStates, ToolDataMsg
from ur_msgs.srv import (
    GetRobotSoftwareVersion, SetAnalogOutput, SetGravity, SetIO, SetPayload,
    SetSpeedSliderFraction)

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

IO = 'io_and_status_controller'
ROBOT_MODES = {v: k for k, v in vars(RobotMode).items()
               if k.isupper() and isinstance(v, int)}
SAFETY_MODES = {v: k for k, v in vars(SafetyMode).items()
                if k.isupper() and isinstance(v, int)}
TOOL_MODES = {249: 'BOOTLOADER', 253: 'RUNNING', 255: 'IDLE'}


class PanelNode(Node):
    """ROS node: subscribes to the controller topics, stores the latest data."""

    def __init__(self):
        super().__init__('my_ur_control_panel')
        self.data = {}
        self.log = []

        def sub(msg_type, topic, key, qos=10):
            self.create_subscription(
                msg_type, topic, lambda m: self.data.__setitem__(key, m), qos)

        sub(IOStates, f'/{IO}/io_states', 'io')
        sub(RobotMode, f'/{IO}/robot_mode', 'robot_mode')
        sub(SafetyMode, f'/{IO}/safety_mode', 'safety_mode')
        sub(ToolDataMsg, f'/{IO}/tool_data', 'tool')
        sub(Bool, f'/{IO}/robot_program_running', 'program_running')
        sub(Float64, '/speed_scaling_state_broadcaster/speed_scaling', 'scaling')
        sub(PoseStamped, '/tcp_pose_broadcaster/pose', 'tcp', qos_profile_sensor_data)
        sub(WrenchStamped, '/force_torque_sensor_broadcaster/wrench', 'wrench',
            qos_profile_sensor_data)

        self.freedrive_pub = self.create_publisher(
            Bool, '/freedrive_mode_controller/enable_freedrive_mode', 10)
        self.script_pub = self.create_publisher(
            String, '/urscript_interface/script_command', 10)
        self.scaling_pub = self.create_publisher(
            SpeedScalingFactor,
            '/scaled_joint_trajectory_controller/speed_scaling_input',
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

        self.srv_clients = {}

    def call(self, srv_type, name, request, on_done=None):
        client = self.srv_clients.get(name)
        if client is None:
            client = self.srv_clients[name] = self.create_client(srv_type, name)
        if not client.service_is_ready():
            self.log.append(f'{name}: service not available')
            return
        future = client.call_async(request)

        def done(f):
            try:
                res = f.result()
                self.log.append(f'{name}: {res}')
                if on_done:
                    on_done(res)
            except Exception as exc:  # noqa: BLE001
                self.log.append(f'{name}: failed ({exc})')
        future.add_done_callback(done)


class Panel(QMainWindow):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.setWindowTitle('UR Control Panel')
        self.resize(760, 640)
        self.version_text = ''

        tabs = QTabWidget()
        tabs.addTab(self.build_status_tab(), 'Status')
        tabs.addTab(self.build_io_tab(), 'IO')
        tabs.addTab(self.build_control_tab(), 'Control')
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(130)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(tabs)
        layout.addWidget(self.log_view)
        self.setCentralWidget(central)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)

    # ---------- Status tab ----------
    def build_status_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self.labels = {}
        for key, title in [
                ('robot_mode', 'Robot mode'), ('safety_mode', 'Safety mode'),
                ('program_running', 'Program running'),
                ('scaling', 'Speed scaling'), ('tcp', 'TCP pose (xyz | quat)'),
                ('wrench', 'Wrench'), ('tool', 'Tool data'),
                ('version', 'Software version')]:
            label = QLabel('-')
            label.setWordWrap(True)
            self.labels[key] = label
            form.addRow(title, label)
        self.din = QLabel('-')
        self.dout = QLabel('-')
        self.ain = QLabel('-')
        self.aout = QLabel('-')
        self.flags = QLabel('-')
        for title, lab in [('Digital in', self.din), ('Digital out', self.dout),
                           ('Flags', self.flags), ('Analog in', self.ain),
                           ('Analog out', self.aout)]:
            lab.setWordWrap(True)
            form.addRow(title, lab)
        btn = QPushButton('Read software version')
        btn.clicked.connect(self.read_version)
        form.addRow(btn)
        return w

    def read_version(self):
        def done(r):
            self.version_text = f'{r.major}.{r.minor}.{r.bugfix}-{r.build}'
        self.node.call(GetRobotSoftwareVersion,
                       '/ur_configuration_controller/get_robot_software_version',
                       GetRobotSoftwareVersion.Request(), done)

    # ---------- IO tab ----------
    def build_io_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        box = QGroupBox('Digital outputs (set_io)')
        grid = QGridLayout(box)
        self.dout_checks = []
        for pin in range(18):
            cb = QCheckBox(f'Pin {pin}')
            cb.clicked.connect(lambda state, p=pin: self.set_digital(p, state))
            self.dout_checks.append(cb)
            grid.addWidget(cb, pin // 6, pin % 6)
        layout.addWidget(box)

        box = QGroupBox('Analog output (set_analog_output)')
        row = QHBoxLayout(box)
        self.ao_pin = QSpinBox()
        self.ao_pin.setRange(0, 1)
        self.ao_val = QDoubleSpinBox()
        self.ao_val.setRange(0.0, 10.0)
        self.ao_val.setDecimals(3)
        self.ao_mode = QCheckBox('Voltage (else current)')
        self.ao_mode.setChecked(True)
        btn = QPushButton('Set')
        btn.clicked.connect(self.set_analog)
        for x in (QLabel('Pin'), self.ao_pin, QLabel('Value'), self.ao_val,
                  self.ao_mode, btn):
            row.addWidget(x)
        layout.addWidget(box)

        box = QGroupBox('Tool voltage (set_io)')
        row = QHBoxLayout(box)
        for volts in (0, 12, 24):
            btn = QPushButton(f'{volts} V')
            btn.clicked.connect(lambda _, v=volts: self.set_tool_voltage(v))
            row.addWidget(btn)
        layout.addWidget(box)
        layout.addStretch()
        return w

    def set_digital(self, pin, state):
        req = SetIO.Request()
        req.fun = SetIO.Request.FUN_SET_DIGITAL_OUT
        req.pin = pin
        req.state = float(state)
        self.node.call(SetIO, f'/{IO}/set_io', req)

    def set_tool_voltage(self, volts):
        req = SetIO.Request()
        req.fun = SetIO.Request.FUN_SET_TOOL_VOLTAGE
        req.state = float(volts)
        self.node.call(SetIO, f'/{IO}/set_io', req)

    def set_analog(self):
        req = SetAnalogOutput.Request()
        req.data.pin = self.ao_pin.value()
        req.data.domain = 1 if self.ao_mode.isChecked() else 0
        req.data.state = self.ao_val.value()
        self.node.call(SetAnalogOutput, f'/{IO}/set_analog_output', req)

    # ---------- Control tab ----------
    def build_control_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        box = QGroupBox('Robot program / driver')
        row = QHBoxLayout(box)
        for text, name in [('Resend robot program', 'resend_robot_program'),
                           ('Hand back control', 'hand_back_control'),
                           ('Zero F/T sensor', 'zero_ftsensor')]:
            btn = QPushButton(text)
            btn.clicked.connect(
                lambda _, n=name: self.node.call(
                    Trigger, f'/{IO}/{n}', Trigger.Request()))
            row.addWidget(btn)
        btn = QPushButton('Stop force mode')
        btn.clicked.connect(lambda: self.node.call(
            Trigger, '/force_mode_controller/stop_force_mode', Trigger.Request()))
        row.addWidget(btn)
        layout.addWidget(box)

        box = QGroupBox('Speed')
        form = QFormLayout(box)
        self.slider = QDoubleSpinBox()
        self.slider.setRange(0.0, 1.0)
        self.slider.setSingleStep(0.05)
        self.slider.setValue(1.0)
        btn = QPushButton('Set speed slider')
        btn.clicked.connect(self.set_speed_slider)
        form.addRow('Speed slider fraction', self.slider)
        form.addRow(btn)
        self.factor = QDoubleSpinBox()
        self.factor.setRange(0.0, 1.0)
        self.factor.setSingleStep(0.05)
        self.factor.setValue(1.0)
        btn = QPushButton('Publish speed scaling input')
        btn.clicked.connect(self.publish_scaling)
        form.addRow('Trajectory scaling factor', self.factor)
        form.addRow(btn)
        layout.addWidget(box)

        box = QGroupBox('Payload (set_payload)')
        form = QFormLayout(box)
        self.mass = QDoubleSpinBox()
        self.mass.setRange(0.0, 50.0)
        self.mass.setSuffix(' kg')
        form.addRow('Mass', self.mass)
        self.cog = []
        for axis in 'xyz':
            sb = QDoubleSpinBox()
            sb.setRange(-1.0, 1.0)
            sb.setDecimals(4)
            sb.setSuffix(' m')
            self.cog.append(sb)
            form.addRow(f'CoG {axis}', sb)
        btn = QPushButton('Set payload')
        btn.clicked.connect(self.set_payload)
        form.addRow(btn)
        layout.addWidget(box)

        box = QGroupBox('Gravity (set_gravity)')
        row = QHBoxLayout(box)
        self.grav = []
        for axis, default in zip('xyz', (0.0, 0.0, 9.81)):
            sb = QDoubleSpinBox()
            sb.setRange(-20.0, 20.0)
            sb.setValue(default)
            self.grav.append(sb)
            row.addWidget(QLabel(axis))
            row.addWidget(sb)
        btn = QPushButton('Set gravity')
        btn.clicked.connect(self.set_gravity)
        row.addWidget(btn)
        layout.addWidget(box)

        box = QGroupBox('Freedrive')
        row = QHBoxLayout(box)
        self.freedrive = QCheckBox('Enable freedrive mode')
        self.freedrive.clicked.connect(self.toggle_freedrive)
        row.addWidget(self.freedrive)
        layout.addWidget(box)
        layout.addStretch()
        return w

    def set_speed_slider(self):
        req = SetSpeedSliderFraction.Request()
        req.speed_slider_fraction = self.slider.value()
        self.node.call(SetSpeedSliderFraction, f'/{IO}/set_speed_slider', req)

    def publish_scaling(self):
        msg = SpeedScalingFactor()
        msg.factor = self.factor.value()
        self.node.scaling_pub.publish(msg)

    def set_payload(self):
        req = SetPayload.Request()
        req.mass = self.mass.value()
        req.center_of_gravity.x, req.center_of_gravity.y, req.center_of_gravity.z = (
            s.value() for s in self.cog)
        req.transition_time = Duration()
        self.node.call(SetPayload, f'/{IO}/set_payload', req)

    def set_gravity(self):
        req = SetGravity.Request()
        req.gravity.header.frame_id = 'base'
        req.gravity.header.stamp = self.node.get_clock().now().to_msg()
        req.gravity.vector.x, req.gravity.vector.y, req.gravity.vector.z = (
            s.value() for s in self.grav)
        self.node.call(SetGravity, '/gravity_update_controller/set_gravity', req)

    def toggle_freedrive(self, state):
        msg = Bool()
        msg.data = bool(state)
        self.node.freedrive_pub.publish(msg)

    # ---------- refresh ----------
    def refresh(self):
        d = self.node.data
        lab = self.labels
        if 'robot_mode' in d:
            lab['robot_mode'].setText(ROBOT_MODES.get(d['robot_mode'].mode, '?'))
        if 'safety_mode' in d:
            lab['safety_mode'].setText(SAFETY_MODES.get(d['safety_mode'].mode, '?'))
        if 'program_running' in d:
            lab['program_running'].setText(str(d['program_running'].data))
        if 'scaling' in d:
            lab['scaling'].setText(f"{d['scaling'].data:.1f} %")
        if 'tcp' in d:
            p = d['tcp'].pose
            lab['tcp'].setText(
                f'{p.position.x:.3f} {p.position.y:.3f} {p.position.z:.3f} | '
                f'{p.orientation.x:.3f} {p.orientation.y:.3f} '
                f'{p.orientation.z:.3f} {p.orientation.w:.3f}')
        if 'wrench' in d:
            w = d['wrench'].wrench
            lab['wrench'].setText(
                f'F: {w.force.x:.2f} {w.force.y:.2f} {w.force.z:.2f} N | '
                f'T: {w.torque.x:.2f} {w.torque.y:.2f} {w.torque.z:.2f} Nm')
        if 'tool' in d:
            t = d['tool']
            lab['tool'].setText(
                f'mode {TOOL_MODES.get(t.tool_mode, t.tool_mode)}, '
                f'{t.tool_output_voltage} V out, {t.tool_current:.2f} A, '
                f'{t.tool_temperature:.1f} C, AI2 {t.analog_input2:.2f}, '
                f'AI3 {t.analog_input3:.2f}')
        lab['version'].setText(self.version_text or '-')
        if 'io' in d:
            io = d['io']

            def fmt(states):
                return ' '.join(f'{s.pin}:{int(s.state)}' for s in states)

            self.din.setText(fmt(io.digital_in_states))
            self.dout.setText(fmt(io.digital_out_states))
            self.flags.setText(fmt(io.flag_states))
            self.ain.setText(' '.join(
                f'{s.pin}:{s.state:.2f}' for s in io.analog_in_states))
            self.aout.setText(' '.join(
                f'{s.pin}:{s.state:.2f}' for s in io.analog_out_states))
            for s in io.digital_out_states:
                if s.pin < len(self.dout_checks):
                    self.dout_checks[s.pin].setChecked(bool(s.state))
        while self.node.log:
            self.log_view.appendPlainText(self.node.log.pop(0))


def main(args=None):
    rclpy.init(args=args, signal_handler_options=rclpy.SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    node = PanelNode()
    app = QApplication(sys.argv)
    panel = Panel(node)
    panel.show()
    spin = QTimer()
    spin.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    spin.start(10)
    code = app.exec_()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(code)


if __name__ == '__main__':
    main()
