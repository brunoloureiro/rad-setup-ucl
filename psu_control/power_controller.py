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
		max_voltage: float = 14.0,
		max_current: float = 1.5,
		monitor_polling_time: float = 20 * MS,
		monitor_log_file = None,
		*,
		initial_state: bool = None,
		initial_voltage: float = None,
		initial_current: float = None,
		device = None,
		serial_port = '/dev/ttyACM0',
		verbose: bool = False,
	):
		self.logger = logger
		self.verbose = verbose

		if update_initial_state:
			if initial_state is None:
				s = (
					f"Power monitor is configured to update initial state, "
					f"but did not receive value to power on/off"
				)
				self.logger.error(s)
				raise ValueError(
					s
				)

			if initial_voltage is None:
				s = (
					f"Power monitor is configured to update initial state, "
					f"but did not receive value for voltage"
				)
				self.logger.error(s)
				raise ValueError(
					s
				)

			if initial_current is None:
				s = (
					f"Power monitor is configured to update initial state, "
					f"but did not receive value for current"
				)
				self.logger.error(s)
				raise ValueError(
					s
				)

		# monitoring settings

		self.max_voltage = max_voltage
		self.max_current = max_current

		if device is None:
			device = ps2000(
				port=serial_port,
				logger=logger,
			)

		self.device = device
		self._monitor_running = False
		try:
			self.init_device(
				update_initial_state = update_initial_state,
				initial_state = initial_state,
				initial_voltage = initial_voltage,
				initial_current = initial_current,
			)

			self._monitor_thread = PowerMonitor(
				self.logger,
				self.device,
				self.max_current,
				self.max_voltage,
				monitor_polling_time,
				monitor_log_file,
				verbose=verbose,
			)
		except Exception as e:
			self.shutdown(cause=e)
			raise e

	def init_device(
		self,
		*,
		update_initial_state: bool,
		initial_state: bool,
		initial_voltage: float,
		initial_current: float,
	):
		self.device.set_remote(True)
		curr_state = self.device.get_output_on()
		if update_initial_state and (curr_state != initial_state):
			self.logger.info(
				f"Initializing the device with {initial_voltage}V and {initial_current}A, "
				f"then turning it {'on' if initial_state else 'off'}"
			)
			self.device.set_voltage(initial_voltage)
			self.device.set_current(initial_current)
			self.device.set_output_on(initial_state)

	def power_on(self):
		if self.verbose:
			self.logger.debug(f"Power controller is turning PSU on.")

		return self.device.set_output_on()

	def power_off(self):
		if self.verbose:
			self.logger.debug(f"Power controller is turning PSU off.")
		return self.device.set_output_off()

	def start_monitor(self):
		if not self._monitor_running:
			if self.verbose:
				self.logger.debug(f"Received signal to start the power monitor.")
			self._monitor_thread.start()

		self._monitor_running = True

	def stop_monitor(self):
		self.logger.info(f"Sending signal from power controller to stop monitor.")
		self._monitor_thread.stop()

	def shutdown(self, cause=None):
		reason_str = f"Reason: {cause}" if cause is not None else ""
		self.logger.info(f"Shutting down the controller!{reason_str}")
		self.device.set_remote(False)
		self.logger.info(f"Disabled remote control for the power supply")
		self.device.close()
		self.logger.info(f"Controller closed the connection to the device. Exiting.")