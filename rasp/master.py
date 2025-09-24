import socket
import os

from utils.const import (
	SEP,
)

from utils import (
	log_debug_and_print,
	log_info_and_print,
	log_warning_and_print,
	log_error_and_print
)

from rasp import (
	BeamController,
	CommandMonitor,
	HeartbeatMonitor,
	FileReceiver,
)

from server.reboot_machine import (
	_select_command_on_switch,
)

_OFF = "OFF"

class Master():
	def __init__(
		self,
		heartbeat_ip="192.168.1.5",
		heartbeat_port=1234,
		heartbeat_timeout=2,
		command_ip="192.168.1.5",
		command_port=1236,
		command_timeout=2,
		transfer_ip="192.168.1.5",
		transfer_port=1238,
		transfer_timeout=2,
		*,
		logger,
		verbose=False,
		beam_verbose=None,
		heartbeat_verbose=None,
		command_verbose=None,
		transfer_verbose=None,
		log_heartbeat_every=10,
		corrupted_output_save_path='/home/unitn/experiment_data/corrupted_output/',
		file_transfer_max_connections=5,
		switch_model='default',
		switch_ip='192.168.1.100',
		switch_port=1,
	):
		self.logger = logger
		self.verbose = verbose

		# TO-DO: Not hard-coded values
		self.switch_model = switch_model
		self.switch_ip = switch_ip
		self.switch_port = int(switch_port)

		if beam_verbose is None:
			beam_verbose = verbose
		self.beam_controller = BeamController(
			logger,
			verbose=beam_verbose,
		)

		if heartbeat_verbose is None:
			heartbeat_verbose = verbose
		self.heartbeat_monitor = HeartbeatMonitor(
			self.beam_controller,
			heartbeat_ip,
			heartbeat_port,
			heartbeat_timeout,
			logger,
			verbose=heartbeat_verbose,
			log_every=log_heartbeat_every,
		)

		if command_verbose is None:
			command_verbose = verbose
		self.command_monitor = CommandMonitor(
			self,
			self.beam_controller,
			command_ip,
			command_port,
			command_timeout,
			logger,
			verbose=command_verbose,
		)

		if transfer_verbose is None:
			transfer_verbose = verbose
		self.transfer_monitor = FileReceiver(
			transfer_ip,
			transfer_port,
			transfer_timeout,
			logger,
			verbose=transfer_verbose,
			download_path=corrupted_output_save_path,
			max_connections=file_transfer_max_connections,
		)

		self._monitor_threads = [
			self.heartbeat_monitor,
			self.command_monitor,
			self.transfer_monitor,
		]

		self.heartbeat_monitor.start()
		self.command_monitor.start()
		self.transfer_monitor.start()

	def stop(self):
		# Not super important to keep at 'info' level
		# but it should only happen once per execution
		log_info_and_print(
			f"Master received signal to stop threads.",
			self.logger,
			self.verbose,
		)
		for t in self._monitor_threads:
			t.stop()

		for t in self._monitor_threads:
			t.join()

		log_info_and_print(
			f"Master finished joining threads. Exiting.",
			self.logger,
			self.verbose,
		)

	def shutdown_board(self, verbose=False):
		log_error_and_print(
			f"Received command to shutdown board due to critical measurement.",
			self.logger,
			self.verbose or verbose,
		)
		off_status = _select_command_on_switch(
			status=_OFF,
			switch_model=self.switch_model,
			switch_port=self.switch_port,
			switch_ip=self.switch_ip,
			logger=self.logger,
		)
		log_error_and_print(
			f"Sent command for switch to turn off. Result: {off_status}",
			self.logger,
			self.verbose or verbose,
		)