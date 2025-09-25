import time

def log_debug_and_print(message, logger, verbose):
	if logger is not None and verbose:
		logger.debug(message)
	if verbose:
		print(f"[DEBUG] [{time.ctime()} - {time.time()}]: " + message)

def log_info_and_print(message, logger, verbose):
	if logger is not None:
		logger.info(message)
	if verbose:
		print(f"[INFO] [{time.ctime()} - {time.time()}]: " + message)

def log_warning_and_print(message, logger, verbose):
	if logger is not None:
		logger.warning(message)
	if verbose:
		print(f"[WARNING] [{time.ctime()} - {time.time()}]: " + message)

def log_error_and_print(message, logger, verbose):
	if logger is not None:
		logger.error(message)
	if verbose:
		print(f"[ERROR] [{time.ctime()} - {time.time()}]: " + message)