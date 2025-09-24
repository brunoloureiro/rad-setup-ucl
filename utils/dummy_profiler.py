class DummyProfiler(object):
	def __init__(self):
		pass

	def __enter__(self, *args, **kwargs):
		return None

	def __exit__(self, *args, **kwargs):
		pass