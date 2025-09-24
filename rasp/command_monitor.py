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
	CMD_OPEN_BEAM,
	CMD_CLOSE_BEAM,
	CMD_SHUTDOWN_BOARD,
)

class CommandMonitor(threading.Thread):
	def __init__(
		self,
		controller,
		beam_controller,
		ip="127.0.0.1",
		port=1236,
		timeout=2,
		logger=None,
		*,
		verbose=False,
	):
		threading.Thread.__init__(self)

		self.controller = controller
		self.beam_controller = beam_controller

		self.ip = ip
		self.port = int(port)
		self.logger = logger
		self.verbose = verbose
		self.timeout = timeout

		self._stop_signal = threading.Event()

		try:
			self._sock = socket.socket(
				socket.AF_INET, # Internet
				socket.SOCK_DGRAM, # UDP
			)
			self._sock.bind((self.ip, self.port))
			self._sock.setblocking(0) # We can still use select() without timeout to have a blocking call
		except Exception as e:
			log_error_and_print(
				f"Could not bind socket for command monitor. Error: {e}",
				self.logger,
				self.verbose,
			)
			raise e

	def run(self, *, verbose=False):
		while not self._stop_signal.is_set():
			cmd, err = self.monitor_command(self.timeout, verbose)
			if cmd is not None:
				self.proc_cmd(cmd, verbose)
		log_debug_and_print(
			f"Command monitor thread is stopping.",
			self.logger,
			self.verbose or verbose,
		)

	def monitor_command(self, timeout, verbose=False):
		if timeout >= 0:
			ready = select.select([self._sock], [], [], timeout)
		else:
			ready = select.select([self._sock], [], []) #blocking call

		if ready[0]:
			data = self._sock.recv(1024)
			if CMD_HEARTBEAT in data:
				log_warning_and_print(
					f"Command monitor got a heartbeat message: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return None, f"heartbeat command"
			elif CMD_OPEN_BEAM in data:
				log_debug_and_print(
					f"Received command to open beam: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return CMD_OPEN_BEAM, ""
			elif CMD_CLOSE_BEAM in data:
				log_debug_and_print(
					f"Received command to close beam: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return CMD_CLOSE_BEAM, ""
			elif CMD_SHUTDOWN_BOARD in data:
				log_debug_and_print(
					f"Received command to shutdown the board: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return CMD_SHUTDOWN_BOARD, ""
			else:
				log_warning_and_print(
					f"Command monitor got an invalid message: {data}",
					self.logger,
					self.verbose or verbose,
				)
				return None, f"invalid command"
		else:
			return None, "timeout"
		#data, addr = self._sock.recvfrom(1024) # buffer size is 1024 bytes		

	def proc_cmd(self, cmd, verbose=False):
		if cmd == CMD_OPEN_BEAM:
			self.beam_controller.open_beam(verbose)
		elif cmd == CMD_CLOSE_BEAM:
			self.beam_controller.close_beam(verbose)
		elif cmd == CMD_SHUTDOWN_BOARD:
			self.controller.shutdown_board(self.verbose or verbose)
		else:
			log_error_and_print(
				f"Proc got an invalid command: {cmd}",
				self.logger,
				self.verbose or verbose,
			)

	def stop(self):
		self._stop_signal.set()