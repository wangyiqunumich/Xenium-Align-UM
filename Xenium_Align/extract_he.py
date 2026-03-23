from aicsimageio import AICSImage
import tifffile
import numpy as np

# 1. Load the CZI file
input_czi = "01.czi"
img = AICSImage(input_czi)

print(f"Successfully opened {input_czi}.")
print(f"Found {len(img.scenes)} scenes (images) inside.")

# 2. Loop through every scene and save it as a separate TIFF
for i, scene_name in enumerate(img.scenes):
    # Tell the reader to focus on the current scene
    img.set_scene(scene_name)
    
    # Extract the image data. 
    # "CYX" tells it to give us the Channels (RGB), Y (Height), and X (Width).
    scene_data = img.get_image_data("CYX", T=0, Z=0)
    
    # 3. Save as a standard TIFF file
    output_filename = f"HE_scene_{i+1}.tiff"
    tifffile.imwrite(output_filename, scene_data)
    
    print(f"Saved: {output_filename}")

print("All H&E scenes extracted successfully!")
