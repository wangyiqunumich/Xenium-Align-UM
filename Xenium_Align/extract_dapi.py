import tifffile
import numpy as np

# Read the original CosMx multi-channel TIFF
input_path = 'TID1_scene5_cosmx.tiff'
img = tifffile.imread(input_path)

# Extract the 3rd channel (index 2) for DAPI
if img.ndim == 3 and img.shape[0] < img.shape[-1]:
    dapi_image = img[2, :, :]
else:
    dapi_image = img[:, :, 2]

# Save the 2D DAPI image as a new TIFF file
output_path = 'TID1_scene5_DAPI_extracted.tiff'
tifffile.imwrite(output_path, dapi_image)

print(f"Success! Saved DAPI image to {output_path}")
