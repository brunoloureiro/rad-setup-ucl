import log_helper as lh

import time

def get_lh_log_file_name():
	return lh.get_log_file_name().split('/')[-1].split('.')[0]

class LHLogger():
	def __init__(self, lock):
		self.lock = lock
		self.info_count = 0
		self.error_count = 0

	def log_info_no_lock(self, info):
		lh.log_info_count(self.info_count)
		self.info_count += 1
		lh.log_info_detail(info)

	def log_error_no_lock(self, e):
		lh.log_error_count(self.error_count)
		self.error_count += 1
		lh.log_error_detail(e)

	def log_info(self, info):
		with self.lock:
			lh.log_info_count(self.info_count)
			self.info_count += 1
			lh.log_info_detail(info)

	def log_error(self, e):
		with self.lock:
			lh.log_error_count(self.error_count)
			self.error_count += 1
			lh.log_error_detail(e)

	# alias
	debug = log_info
	info = log_info
	warning = log_info
	error = log_error