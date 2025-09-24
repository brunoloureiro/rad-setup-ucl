def test_file_name_functions():
	datasets = ['ILSVRC2012', 'somethingelse']
	splits = ['val','train']
	extensions = ['JPEG', 'jpg', 'png']
	images = ['00000022', 'ILSVRC2012_val_000.JPEG', '00000100', '00000228', '00000274.jpg', 'hfdskjg.png', 'ILSVRC2012_notanimage', 'train_choo', 'numbers.JPEG', 'somethingelse_train_smt.png']
	positive_results = []	
	for dataset in datasets:
		print(f"Dataset: {dataset}")
		for split in splits:
			print(f"--- Split: {split}")
			for extension in extensions:
				print(f"------ Extension: {extension}")
				for img_id in images:
					print(f"--------- Image: {img_id}")
					is_fname = is_file_name(img_id, dataset, split, extension)
					fname = get_image_file_name(img_id, dataset, split, extension)
					print(f"Is file name: {is_fname}")
					print(f"Resulting file name: {fname}")
					print("")
					if is_fname:
						positive_results.append((dataset, split, extension, img_id, fname))
					#time.sleep(2)
				print("")
			print("")
		print("")

	print("IDs that were file names:")
	for r in positive_results:
		print(r)