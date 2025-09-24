from typing import (
	Optional,
)

import threading
import datetime
import time
from pathlib import Path

from .power_stats import (
	PowerStats,
)

class PowerMonitor(threading.Thread):
	def __init__(
		self,
		logger,
		device,
		max_current: float,
		max_voltage: float,
		polling_time: float,
		log_file: Optional[str],
		verbose: bool = False,
	):
		threading.Thread.__init__(self, daemon=True)

		self.logger = logger
		self.device = device
		self.max_current = max_current
		self.max_voltage = max_voltage
		self.polling_time = polling_time

		self.log_file = log_file
		self._file_available = False
		self.verbose = verbose

		if log_file is not None:
			try:
				p = Path(log_file).parent
				p.mkdir(exist_ok=True, parents=True)
				f = open(log_file, 'a')
				f.close()
				self._file_available = True
				if self.verbose:
					self.logger.info(f"Successfully opened power measurement file {log_file}")
			except FileNotFoundError as e:
				self.logger.error(f"Error opening log file for power monitor: {e}")
				self._file_available = False
				raise e

		self._stop_signal = threading.Event()

	def stop(self):
		self.logger.info(f"Power monitor received signal to stop.")
		self._stop_signal.set()

	def run(self):
		if self.log_file is not None and self._file_available:
			try:
				if self.verbose:
					self.logger.debug(f"Starting power monitor with logging enabled")
				with open(self.log_file, 'a') as f:
					if self.verbose:
						self.logger.debug(f"Successfully opened measurement log file, starting thread")
					self._run_monitor(f)
			except FileNotFoundError as e:
				self.logger.error(f"Error opening log file for power monitor: {e}")
				raise e
		else:
			if self.verbose:
				self.logger.debug(f"Starting power monitor without logging")
			self._run_monitor(None)

		self.logger.info(f"Stopping power monitor")

	def shutoff_device(self):
		self.device.set_remote(True)
		self.device.set_output_off()

	def _run_monitor(self, file=None):
		while not self._stop_signal.is_set():
			stats: PowerStats = self.device.get_current_stats()

			if self.max_voltage is not None and stats.voltage > self.max_voltage:
				self.shutoff_device()
				self.logger.warning(
					f"Turning off power supply: voltage is {stats.voltage}V "
					f"(monitor is configured with a maximum of {self.max_voltage}V)"
				)

			if self.max_current is not None and stats.current > self.max_current:
				self.shutoff_device()
				self.logger.warning(
					f"Turning off power supply: current is {stats.current}A "
					f"(monitor is configured with a maximum of {self.max_current}A)"
				)

			now = datetime.datetime.now()

			if file is not None:
				s = f"[{now}] {stats}\n"
				file.write(s)

			if self.verbose:
				self.logger.debug(f"Iteration done: {stats}")
			time.sleep(self.polling_time)