from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# 1. Load the original H&E TIF
file_path = '../Dataset/TID1_HE_scene_5.tif'
img = Image.open(file_path)

# 2. Force a physical pixel flip (Left to Right)
flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)

# 3. Save it and overwrite our REFLECTED.tif
output_path = '../Dataset/TID1_HE_scene_5_REFLECTED.tif'
flipped_img.save(output_path)

print(f"Success! Physically flipped image saved to: {output_path}")