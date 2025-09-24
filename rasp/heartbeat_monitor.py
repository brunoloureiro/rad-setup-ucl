import threading
import socket
import time
import select

from utils import (
	log_debug_and_print,
	log_info_and_print,
	log_warning_and_print,
	log_error_and_print
)

from utils.const import (
	CMD_HEARTBEAT,
)

# TO-DO
# use enumerate or something decent
NO_ERROR = ""
ERR_TIMEOUT = "timeout"
STOPPED_WHILE_WAITING_FIRST_BEAT = "stopped"

class HeartbeatMonitor(threading.Thread):
	def __init__(
		self,
		beam_controller,
		monitor_ip="127.0.0.1",
		monitor_port=1234,
		timeout=2,
		logger=None,
		*,
		verbose=False,
		log_every=10,
	):
		threading.Thread.__init__(self, daemon=True)

		self.beam_controller = beam_controller

		self.ip = monitor_ip
		self.port = int(monitor_port)

		self.timeout = timeout

		self.logger = logger
		self.log_every = log_every
		self.verbose = verbose

		self._stop_signal = threading.Event()

		try:
			self._sock = socket.socket(
				socket.AF_INET, # Internet
				socket.SOCK_DGRAM, # UDP
			)
			self._sock.bind((self.ip, self.port))
			self._sock.setblocking(0)
		except Exception as e:
			log_error_and_print(
				f"Could not bind socket for heartbeat monitor. Error:{e}",
				self.logger,
				self.verbose or verbose,
			)
			raise e

	def run(self, *, verbose=False):
		while not self._stop_signal.is_set():
			try:
				err = self.monitor_heartbeat(verbose)
			finally:
				self.beam_controller.close_beam(verbose)
			log_warning_and_print(
				f"Stopped monitoring heartbeat. Reason: {err}",
				self.logger,
				self.verbose or verbose,
			)
			self.restart_monitor(verbose)
			log_debug_and_print(
				f"Restarted the heartbeat monitor.",
				self.logger,
				self.verbose or verbose,
			)
		log_debug_and_print(
			f"Heartbeat monitor thread is stopping.",
			self.logger,
			self.verbose or verbose,
		)

	def restart_monitor(self, verbose=False):
		pass

	# TO-DO:
	# determine if this class should have these functions or if something else should
	# 	it might be a good idea to have a "Server" class that includes
	# 		a HB monitor, a CMD monitor, some other (e.g., beam) monitors if needed, ...

	def stop(self):
		self._stop_signal.set()

	def monitor_heartbeat(self, verbose=False):
		log_debug_and_print(
			f"Waiting for first heartbeat.",
			self.logger,
			self.verbose or verbose,
		)

		heartbeat = False
		while not heartbeat and not self._stop_signal.is_set():
			heartbeat, err = self.wait_for_heartbeat(self.timeout, verbose)
		if not heartbeat: # stop signal is set
			return STOPPED_WHILE_WAITING_FIRST_BEAT
		#assert heartbeat, "Heartbeat monitor somehow stopped waiting for heartbeat even though it did not get any."
		log_debug_and_print(
			f"Got first heartbeat at {time.ctime()} ({time.time()}). Entering monitoring stage.",
			self.logger,
			self.verbose or verbose,
		)
		last_heartbeat = time.time()
		heartbeat_number = 0
		while not self._stop_signal.is_set():
			heartbeat, err = self.wait_for_heartbeat(self.timeout, verbose)
			if heartbeat:
				current_time = time.time()
				if current_time - last_heartbeat > self.timeout:
					log_warning_and_print(
						f"Got a heartbeat but somehow it should have timed out",
						self.logger,
						self.verbose or verbose,
					)
					return ERR_TIMEOUT

				heartbeat_number += 1
				if heartbeat_number % self.log_every == 0:
					log_debug_and_print(
						f"Heartbeat still alive after {heartbeat_number} beats.",
						self.logger,
						self.verbose or verbose,
					)
			else:
				return err

			last_heartbeat = current_time

	def wait_for_heartbeat(self, timeout, verbose):
		if timeout >= 0:
			ready = select.select([self._sock], [], [], timeout)
		else:
			ready = select.select([self._sock], [], []) #blocking call

		if ready[0]:
			data = self._sock.recv(1024)
			if CMD_HEARTBEAT not in data:
				log_warning_and_print(
					f"Heartbeat monitor got a message other than a heartbeat: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return False, f"wrong message: {data}"
			#log_debug_and_print(
			#	f"Received heartbeat: {data}",
			#	self.logger,
			#	self.verbose or verbose,
			#)
			return True, NO_ERROR
		else:
			return False, ERR_TIMEOUT