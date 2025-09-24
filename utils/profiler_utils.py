from torch.profiler import (
	profile,
	record_function,
	ProfilerActivity,
)

from utils import (
	DummyProfiler,
)

def get_profiler(
	include_profiler,
	function_name,
	*,
	activities=[ProfilerActivity.CPU],
	record_shapes=True,
	use_cuda=False,
	profile_memory=True,
):
	# TO-DO:
	# replace manual args with *args and **kwargs
	if include_profiler:
		profiler = profile(activities=activities, record_shapes=record_shapes, use_cuda=use_cuda, profile_memory=profile_memory)
		p_record = record_function(function_name)
	else:
		profiler = DummyProfiler()
		p_record = DummyProfiler()

	return profiler, p_record