import argparse
import os
from aicsimageio import AICSImage
import tifffile
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Extract scenes from CZI file to TIFF")
    parser.add_argument('-input', required=True, help="Path to input CZI file")
    parser.add_argument('-output_prefix', required=True, help="Prefix for output files (e.g., ../Dataset/TID1_HE)")
    args = parser.parse_args()

    img = AICSImage(args.input)
    print(f"Successfully opened {args.input}.")
    print(f"Found {len(img.scenes)} scenes (images) inside.")

    # Create directory if it doesn't exist
    out_dir = os.path.dirname(args.output_prefix)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Loop through every scene and save it as a separate TIFF
    for i, scene_name in enumerate(img.scenes):
        img.set_scene(scene_name)
        scene_data = img.get_image_data("CYX", T=0, Z=0)
        
        output_filename = f"{args.output_prefix}_scene_{i+1}.tif"
        tifffile.imwrite(output_filename, scene_data)
        print(f"Saved: {output_filename}")

    print("All H&E scenes extracted successfully!")

if __name__ == "__main__":
    main()