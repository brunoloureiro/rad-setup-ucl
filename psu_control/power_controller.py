from .ps2000 import (
	ps2000
)

from .power_monitor import (
	PowerMonitor,
)

MS = 1 / 1000

class PowerController:
	def __init__(
		self,
		logger,
		update_initial_state: bool,
		initial_state: bool = True,
		initial_voltage: float = 12.0,
		initial_current: float = 1.3,
		max_voltage: float = 14.0,
		max_current: float = 1.5,
		monitor_polling_time: float = 20 * MS,
		monitor_log_file = None,
		*,
		device = None,
		serial_port = '/dev/ttyACM0',
		verbose: bool = False,
	):
		# monitoring settings

		self.max_voltage = max_voltage
		self.max_current = max_current
		self.logger = logger

		if device is None:
			device = ps2000(
				port=serial_port,
				logger=logger,
			)

		self.device = device
		self.verbose = verbose
		self._monitor_running = False
		try:
			self.init_device(
				update_initial_state,
				initial_state,
				initial_current,
				initial_voltage,
			)

			self._monitor_thread = PowerMonitor(
				self.logger,
				self.device,
				self.max_current,
				self.max_voltage,
				monitor_polling_time,
				monitor_log_file,
			)
		except Exception as e:
			self.shutdown()

	def init_device(
		self,
		update_initial_state: bool,
		initial_state: bool,
		initial_voltage: float,
		initial_current: float,
	):
		self.device.set_remote(True)
		curr_state = self.device.get_output_on()
		if update_initial_state and (curr_state != initial_state):
			self.device.set_voltage(initial_voltage)
			self.device.set_current(initial_current)
			self.device.set_output_on(initial_state)

	def power_on(self):
		return self.device.set_output_on()

	def power_off(self):
		return self.device.set_output_off()

	def monitor(self):
		if not self._monitor_running:
			self._monitor_thread.start()

		self._monitor_running = True

	def shutdown(self):
		self.device.set_remote(False)
		self.device.close()