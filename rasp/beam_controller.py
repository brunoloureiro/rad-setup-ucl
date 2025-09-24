import threading
import time
REAL_RASP = False
if REAL_RASP:
	from gpiozero import LED
else:
	class LED:
		def __init__(self, pin, initial_value=False):
			pass

		def _on(self):
			print(f"Logical ON")

		def _off(self):
			print("Logical OFF")


from utils import (
	log_debug_and_print,
	log_info_and_print,
	log_warning_and_print,
	log_error_and_print,
)

class BeamController():
	def __init__(
		self,
		logger,
		pin=24,
		*,
		verbose=False,
	):
		self.logger = logger
		self.verbose = verbose

		self._beam = LED(pin, initial_value=False)
		self._beam_open = False
		self._beam_lock = threading.Lock()

	@property
	def beam(self):
		return self._beam_open

	def open_beam(self, verbose=False):
		with self._beam_lock:
			# only log if it was closed before
			if not self._beam_open:
				# keeping this log at info level since it is important
				log_info_and_print(
					"Turning beam on.",
					self.logger,
					self.verbose or verbose,
				)

			# open AFTER trying to log, to be safe
			self._beam.on()
			self._beam_open = True

	def close_beam(self, verbose=False):
		with self._beam_lock:
			# close BEFORE trying to log, to be safe
			self._beam.off()

			# only log if it was open before
			if self._beam_open:
				# keeping this log at info level since it is important
				log_info_and_print(
					"Turning beam off.",
					self.logger,
					self.verbose or verbose,
				)

			self._beam_open = False
