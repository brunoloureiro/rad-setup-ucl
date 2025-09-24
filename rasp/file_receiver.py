import threading
import socket
import time
import select
from pathlib import Path

from utils import (
	log_debug_and_print,
	log_info_and_print,
	log_warning_and_print,
	log_error_and_print
)

from utils.const import (
	SEP,
	CMD_DOWNLOAD_FILE,
	DATA_CHUNK_SIZE,
)

class FileReceiver(threading.Thread):
	def __init__(
		self,
		transfer_ip="127.0.0.1",
		transfer_port=1238,
		timeout=5,
		logger=None,
		*,
		verbose=False,
		download_path='../data/received_files/',
		max_connections=5,
	):
		threading.Thread.__init__(self, daemon=True)

		self.transfer_ip = transfer_ip
		self.transfer_port = int(transfer_port)

		self.timeout = timeout

		self.logger = logger
		self.verbose = verbose

		self.download_path = download_path
		Path(self.download_path).mkdir(exist_ok=True, parents=True)

		self.max_connections = max_connections

		self._stop_signal = threading.Event()

		try:
			self._listener_sock = socket.socket()
			self._listener_sock.bind((self.transfer_ip, self.transfer_port))
			self._listener_sock.listen(self.max_connections)
			self._listener_sock.settimeout(self.timeout)
		except Exception as e:
			log_error_and_print(
				f"Could not bind socket for file receiver. Error: {e}",
				self.logger,
				self.verbose,
			)
			raise e

	def stop(self):
		self._stop_signal.set()

	def run(self, *, verbose=False):
		while not self._stop_signal.is_set():
			try:
				self.wait_for_file(self.timeout, verbose)
			except socket.timeout as e:
				pass
				# TO-DO:
				# Maybe add other exceptions to the list
				# or add another except block
				# e.g., if file transfer fails mid-transfer
				# or if saving the file goes wrong for whatever reason
				#log_debug_and_print(
				#	f"Timed out while waiting for file. Going back to waiting.",
				#	self.logger,
				#	self.verbose or verbose,
				#)
		log_debug_and_print(
			f"File receiver thread is stopping.",
			self.logger,
			self.verbose or verbose,
		)

	def wait_for_file(self, timeout, verbose=False):
		# TO-DO:
		# Add a timeout or something so the server can exit
		# after we are no longer running the script on the DUT
		_client_sock, client_addr = self._listener_sock.accept()
		try:
			print_every=1000*1000
			print_threshold = print_every
			buff_size = DATA_CHUNK_SIZE

			log_debug_and_print(
				f"Received download request, starting.",
				self.logger,
				self.verbose or verbose,
			)

			data = _client_sock.recv(buff_size)
			file_name, file_size, file_dir, ovflow = data.split(bytes(SEP, encoding='ascii'))

			file_name = file_name.decode('ascii')
			file_size = int(file_size.decode('ascii'))
			file_dir = file_dir.decode('ascii')

			if ovflow:
				data = ovflow
				received_bytes = len(ovflow)
			else:
				data = None
				received_bytes = 0

			log_debug_and_print(
				f"Downloading {file_name} with size {file_size}.",
				self.logger,
				self.verbose or verbose,
			)

			#might be useful:
			#os.path.basename(filename)
			save_path = Path(self.download_path) / file_dir
			save_path.mkdir(exist_ok=True, parents=True)
			if Path(save_path / file_name).exists():
				log_error_and_print(
					f"OVERWRITING FILE: File {file_name} already exists in {save_path}.",
					self.logger,
					self.verbose or verbose,
				)
			with open(save_path / file_name, 'wb') as f:
				if data is not None:
					f.write(data)
				while received_bytes < file_size:
					data = _client_sock.recv(buff_size)
					f.write(data)
					received_bytes += len(data)

					if received_bytes > print_threshold:
						#print(f"Received {received_bytes} out of {file_size}...")
						print_threshold += print_every
			# keeping this log at info level since it is (kind of) important
			log_info_and_print(
				f"Finished saving file {save_path/file_name}",
				self.logger,
				self.verbose or verbose,
			)
		finally:
			_client_sock.close()