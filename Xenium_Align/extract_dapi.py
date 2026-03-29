import argparse
import tifffile
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Extract DAPI channel from multi-channel TIFF")
    parser.add_argument('-input', required=True, help="Path to input multi-channel TIFF")
    parser.add_argument('-output', required=True, help="Path to output 2D DAPI TIFF")
    args = parser.parse_args()

    print(f"Reading {args.input}...")
    img = tifffile.imread(args.input)

    # Extract the 3rd channel (index 2) for DAPI
    if img.ndim == 3 and img.shape[0] < img.shape[-1]:
        dapi_image = img[2, :, :]
    else:
        dapi_image = img[:, :, 2]

    tifffile.imwrite(args.output, dapi_image)
    print(f"Success! Saved DAPI image to {args.output}")

if __name__ == "__main__":
    main()