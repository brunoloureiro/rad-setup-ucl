from pathlib import Path
import random
import sys
import os

import torch
from torchvision.models.feature_extraction import create_feature_extractor

def get_dimension_str(tensor):
	tensor_dim = ''
	for d in tensor.size():
		tensor_dim += f"{d}x"
	return tensor_dim[:-1]

def get_flattened_tensor_str(output):
	s = ''
	for layer in output:
		tensor_dim = get_dimension_str(output[layer])

		s += f" LayerName:{layer} TensorDim:{tensor_dim} Tensors:["
		for t in torch.flatten(output[layer]):
			s+= f"{t},"
		s = s[:-1] + "]"
	return s

def save_tensor(*args, **kwargs):
	torch.save(*args, **kwargs)

def get_local_images(imgs_info, images_path, transforms=None):
	images = [Image.open(images_path + "/" + img_info['file_name']) for img_info in imgs_info]

	if transforms is not None:
		images = [transforms(i) for i in images]

	return images

def get_utils_images(imgs_info, images_path, utils):
	#images = [utils.prepare_input_from_uri(images_path + "/" + img_info['file_name']) for img_info in imgs_info]

	images = {}
	error_loading = False
	for img_info in imgs_info:
		try:
			images[img_info['id']] = utils.prepare_input_from_uri(images_path + "/" + img_info['file_name'])
		except Exception as e:
			print(f"Error when preparing image {img_info['file_name']}.\n{e}\n")
			error_loading = True

	if error_loading:
		#exit(-1)
		pass

	return images

# TO-DO:
# more thorough test
def is_file_name(img_id, dataset, split, extension):
	slice_start = (len(extension) + 1) * -1
	img_extension = img_id[slice_start:]
	if '.' + extension == img_extension:
		return True

	return dataset in img_id and split in img_id and extension in img_id

def get_image_file_name(img_id, dataset, split, extension):
	#ILSVRC2012_val_00000285.JPEG
	if is_file_name(img_id, dataset, split, extension):
		return img_id

	s = ''

	if dataset is not None:
		s+= f"{dataset}_"

	if split is not None:
		s+= f"{split}_"

	s += f"{img_id}.{extension}"

	return s

def load_image(
	img_id,
	path,
	dataset='ILSVRC2012',
	split='val',
	extension='JPEG',
	*,
	utils_hub='NVIDIA/DeepLearningExamples:torchhub',
	utils_name='nvidia_convnets_processing_utils',
	compute_file_name=True,
):
	utils = torch.hub.load(utils_hub, utils_name)
	if compute_file_name:
		file_name = get_image_file_name(img_id, dataset, split, extension)
	else:
		file_name = img_id #disable computing file name in case something goes wrong
	try:
		img = utils.prepare_input_from_uri(path + "/" + file_name)
	except Exception as e:
		print(f"Error when preparing image {img_id}.\n{e}\n")
		img = None

	return img

def quiet_pick_n(output, n, utils):
	stdout = sys.stdout

	with open(os.devnull, 'w') as sys.stdout:
		results = utils.pick_n_best(predictions=output, n=n)

	sys.stdout = stdout

	return results

def get_golden_output(img_id, golden_path):
	#golden = {img_info['id']:torch.load(Path(golden_path)/f"{img_info['id']}.pt", map_location='cpu') for img_info in infos}
	#golden = [None for img_info in infos]

	return torch.load(Path(golden_path)/f"{img_id}.pt", map_location='cpu')

	#return golden

def simulate_seu(output, error_chance=0.05):
	if random.random() < error_chance:
		idx = random.choice(range(0,len(output)))
		output[idx] += 128

	return output

def _is_leaf_layer(layer):
	return not "Sequential".lower() in str(layer)[:15].lower()

def is_leaf(name, layer):
	if name == "":
		return False
	try:
		parts = name.split('.')
		int(parts[-1])
		return False
	except:
		# layers named without any dots are avgpool and fc (hopefully)
		# so they will throw an exception on split
		# but I will add an additional test to make sure they are not numbers (should never happen)
		try:
			int(name)
			return False
		except:
			pass
		# additionally,
		# layers that end in a number (e.g., layers.0) are not leaves, but complex/sequential layers
		# so only layers that do not end in a number will throw an exception on type cast to int
		return _is_leaf_layer(layer)

def reload_nn_layers(model_url, model_name, device):
	nn = reload_nn_final_layer(model_url, model_name, device)

	layers = {}
	excluded_layers = {}
	for name, layer in nn.named_modules():
		if is_leaf(name, layer):
			layers[name] = name
		else:
			excluded_layers[name] = layer

	return create_feature_extractor(nn, return_nodes=layers).to(device)

def reload_nn_final_layer(model_url, model_name, device):
	nn = torch.hub.load(model_url, model_name, pretrained=True)
	return nn.eval().to(device)

# TO-DO:
# more thorough testing
def compute_inference_error_tensor(output, golden, threshold=0):
	# flatten is probably not needed
	#output = torch.flatten(output)
	#golden = torch.flatten(golden)

	diff = output - golden

	diff = abs(diff) > abs(golden) * threshold
	
	return torch.any(diff)

def compute_inference_error(output, golden, threshold=0):
	inference_error = False
	error_layers = {}

	for layer in output:
		#layer_error = compute_inference_error_tensor(output[layer], golden[layer], threshold)
		layer_error = not torch.allclose(output[layer], golden[layer])

		inference_error = inference_error or layer_error # only one true/false for the entire NN

		error_layers[layer] = layer_error

	return inference_error, error_layers

def get_object_methods(obj):
	return [method_name for method_name in dir(obj) if callable(getattr(obj, method_name))]

def using_gpu(device):
	return "gpu" in str(device) or "cuda" in str(device)

def percent_str_to_float(s):
	return float(s[:-1])/100

def similar_preds(preds, threshold=.01):
	n_preds = len(preds[0][0])
	for i in range(0, n_preds):
		current_pred = preds[0][0][i]
		for p in preds:
			pred_class, pred_prob = p[0][i]
			if pred_class != current_pred[0]:
				return False
			pred_diff = percent_str_to_float(pred_prob) - percent_str_to_float(current_pred[1])
			if abs(pred_diff) > threshold:
				return False

	return True

def final_layer(nn, name):
	layer_name = final_layer_name(name)
	return nn[layer_name]

def final_layer_name(name):
	if name == 'resnet':
		return 'fc'
	elif name == 'deit':
		return 'head'
	else:
		raise Exception(f"NN not supported: {name}")