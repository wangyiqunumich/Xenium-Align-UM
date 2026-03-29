import tifffile
import numpy as np

# 1. Load the original H&E TIF
file_path = '../Dataset/TID1_HE_scene_5.tif'
print(f"Reading {file_path}...")
img = tifffile.imread(file_path)

# 2. Force a true mathematical matrix flip (Left to Right)
# We use numpy slicing to literally reverse the order of the pixels along the X-axis.
if img.ndim == 3 and img.shape[2] in [3, 4]: 
    # Shape is (Y, X, RGB) - Standard H&E
    flipped_img = img[:, ::-1, :]
elif img.ndim == 3 and img.shape[0] in [3, 4]: 
    # Shape is (RGB, Y, X)
    flipped_img = img[:, :, ::-1]
else: 
    # Shape is (Y, X) - Grayscale
    flipped_img = img[:, ::-1]

# 3. Save it as the standard name the pipeline expects
# (Since we updated the python script to look directly for TID1_HE.tif)
output_path = '../Dataset/TID1_HE.tif'
print(f"Saving mathematically flipped image to {output_path}...")
tifffile.imwrite(output_path, flipped_img)

print(f"Success! Image data matrix physically reversed and saved.")