# End-to-End Image Alignment: Nanostring CosMx to Xenium-Align-UM

This tutorial walks through the process of aligning standard H&E tissue images with Nanostring CosMx spatial transcriptomics data using the `Xenium-Align-UM` pipeline. 

Because this pipeline was natively built for 10x Genomics Xenium data, this guide includes the necessary steps to extract your raw images and safely "disguise" your CosMx coordinate data so the pipeline accepts it without requiring complex source-code modifications.

---

## Prerequisites & Folder Structure
Before beginning, ensure your working directory looks like this:
```text
Project_Folder/
├── Xenium_Align/                  # The cloned pipeline repository
│   ├── extract_dapi.py
│   ├── extract_he.py
│   ├── cosmx_to_xenium_translator.py
│   └── xenium_alignment_for_keypoints.py
└── Dataset/                       # Your data folder
    ├── TID1_scene5_cosmx.tiff     # Raw CosMx multi-channel TIFF
    ├── 01.czi                     # Raw H&E brightfield image
    ├── ECSL7731_SLLLYT1D1_metadata_file.csv # CosMx metadata
    └── ECSL7731_SLLLYT1D1-polygons.csv      # CosMx cell boundaries
```

---

## Step 1: Image Extraction
The alignment pipeline requires 2D, single-channel `.tif` images for both DAPI (nuclear stain) and H&E. Raw outputs from microscopes and CosMx machines are often multi-channel or `.czi` formats that must be split first.

### 1a. Extract DAPI from CosMx TIFF
**Why:** The raw CosMx TIFF contains multiple imaging channels. The pipeline only needs the DAPI channel to locate the cells.
**When:** Run this first to isolate the DAPI image.

**Script:** `extract_dapi.py`
```python
import tifffile
import numpy as np

# Read the original CosMx multi-channel TIFF
input_path = '../Dataset/TID1_scene5_cosmx.tiff'
img = tifffile.imread(input_path)

# Extract the 3rd channel (index 2) for DAPI
if img.ndim == 3 and img.shape[0] < img.shape[-1]:
    dapi_image = img[2, :, :]
else:
    dapi_image = img[:, :, 2]

# Save the 2D DAPI image as a new TIFF file
output_path = '../Dataset/TID1_scene5_DAPI_extracted.tiff'
tifffile.imwrite(output_path, dapi_image)

print(f"Success! Saved DAPI image to {output_path}")
```

### 1b. Extract H&E from `.czi`
**Why:** H&E images are often scanned into proprietary Zeiss `.czi` files containing multiple scenes. The pipeline needs a standard `.tif`.
**When:** Run this to unpack the brightfield image.

**Script:** `extract_he.py`
```python
from aicsimageio import AICSImage
import tifffile

input_czi = "../Dataset/01.czi"
img = AICSImage(input_czi)

# Extract the first scene (Channels, Y, X)
img.set_scene(img.scenes[0])
scene_data = img.get_image_data("CYX", T=0, Z=0)

output_filename = "../Dataset/HE_scene_1.tiff"
tifffile.imwrite(output_filename, scene_data)
print(f"Saved H&E image to {output_filename}")
```

---

## Step 2: Disguising CosMx Data as Xenium Data
**Why is this necessary?** The Xenium-Align-UM pipeline uses a strict third-party data reader (`spatialdata_io`). If it does not see a perfectly formatted 10x Xenium output folder (including compressed coordinate files and a `cell_feature_matrix.h5` gene expression file), it will assume the data is corrupted and crash immediately. Nanostring CosMx outputs standard `.csv` files with different column names and no `.h5` matrix.

**What does the translator script do?**
1. **Maps Coordinates:** It reads your CosMx metadata and polygon CSVs, extracts the geometric coordinates, and renames the columns to match Xenium exactly (e.g., translating CosMx `cellID` to Xenium `cell_id`).
2. **Compresses:** It saves these translated files as `cells.csv.gz` and `cell_boundaries.csv.gz`.
3. **Bypasses the Matrix Check:** The alignment math *only* uses physical coordinates; it doesn't actually need gene expression. The script generates an empty, dummy `cell_feature_matrix.h5` file solely to satisfy the reader's strict requirements and allow the pipeline to proceed.

**When:** Run this after your images are extracted, but *before* you run the alignment pipeline.

**Script:** `cosmx_to_xenium_translator.py`
```python
import pandas as pd
import h5py
import numpy as np
import json

def main():
    dataset_dir = "../Dataset/"
    cosmx_meta = dataset_dir + "ECSL7731_SLLLYT1D1_metadata_file.csv"
    cosmx_poly = dataset_dir + "ECSL7731_SLLLYT1D1-polygons.csv"
    
    df_meta = pd.read_csv(cosmx_meta)
    df_poly = pd.read_csv(cosmx_poly)
    
    # Translate to cells.csv.gz
    df_cells = pd.DataFrame({
        'cell_id': df_meta['cell_ID'],
        'x_centroid': df_meta['CenterX_global_px'],
        'y_centroid': df_meta['CenterY_global_px']
    })
    df_cells.to_csv(dataset_dir + "cells.csv.gz", index=False, compression='gzip')

    # Translate to cell_boundaries.csv.gz
    df_bounds = pd.DataFrame({
        'cell_id': df_poly['cellID'],
        'vertex_x': df_poly['x_global_px'],
        'vertex_y': df_poly['y_global_px']
    })
    df_bounds.to_csv(dataset_dir + "cell_boundaries.csv.gz", index=False, compression='gzip')

    # Create dummy matrix
    with h5py.File(dataset_dir + 'cell_feature_matrix.h5', 'w') as f:
        matrix = f.create_group('matrix')
        matrix.create_dataset('barcodes', data=np.array([], dtype='S1'))
        matrix.create_dataset('data', data=np.array([], dtype='i4'))
        matrix.create_dataset('indices', data=np.array([], dtype='i4'))
        matrix.create_dataset('indptr', data=np.array([0], dtype='i4'))
        matrix.create_dataset('shape', data=np.array([0, 0], dtype='i4'))
        features = matrix.create_group('features')
        features.create_dataset('id', data=np.array([], dtype='S1'))
        features.create_dataset('name', data=np.array([], dtype='S1'))
        features.create_dataset('feature_type', data=np.array([], dtype='S1'))

    # Create dummy experiment file
    with open(dataset_dir + "experiment.xenium", "w") as f:
        json.dump({"major_version": 1, "minor_version": 0, "pixel_size": 0.12}, f)

if __name__ == "__main__":
    main()
```
Run it in your terminal: `python cosmx_to_xenium_translator.py`

---

## Step 3: Run the Alignment Pipeline
**Why:** Now that your images are formatted and your CosMx coordinates are successfully disguised, the pipeline can analyze the physical cell geometries to calculate the mathematical transformation needed to overlay the H&E image onto the spatial coordinates.
**When:** This is the final step, run only when your `Dataset` folder contains the `.tif` images, the `.csv.gz` files, and the `.h5` file.

Run the pipeline using `nohup` (so it runs in the background even if you close your terminal):

```bash
nohup python xenium_alignment_for_keypoints.py \
    -sample TID1 \
    -preservation_method ff \
    -data_file_path ../Dataset/ \
    -crop_radius_pixel 400 \
    -center_move_pixel 300 \
    -check_cell_num 100 \
    -mip_ome_extract_ratio 0.125 \
    -mip_ome_extract_min 50 \
    -segment_method cellpose \
    -overlap_type overlap_ave \
    -overlap_threshold_ave 0.9 \
    -keypoints_min_num 15 \
    -epoch_num 30 \
    > step3_keypoints.log 2>&1 &
```

### Monitoring the Process
To watch the pipeline process your images and calculate keypoints in real-time, view the log output:
```bash
tail -f step3_keypoints.log
```
*(Press `Ctrl + C` to stop watching the log; the script will continue running safely in the background).*

## Prerequisites: Required Files for Step 3 (Xenium Alignment)

Before running `xenium_alignment_for_keypoints.py` (Step 3), your `Dataset` folder must be strictly formatted as a standard **10x Genomics Xenium** output directory. 

Because the alignment script uses the `spatialdata_io.xenium()` function to load the dataset, it will **fail** if it only finds raw `.tif` images or raw CosMx `.csv` files. The reader physically cannot parse standard CSVs or raw TIFFs without the accompanying Xenium metadata and parquet structures.

### Current State vs. Required State

**What you currently have:**
* `TID1_DAPI_scene_5.tif` (Raw DAPI image)
* `TID1_HE_scene_5.tif` (Raw H&E image)
* *Various CosMx tabular outputs (e.g., transcript and polygon CSVs)*

**What Step 3 strictly requires:**
To bypass the `spatialdata_io` reader checks, your dataset folder must contain the following specific Xenium-formatted files:

#### 1. The Xenium Configuration File
* **Missing File:** `experiment.xenium`
* **Why it is required:** This is the master metadata file. `spatialdata_io` reads this first to determine the physical pixel size and the software version. If this file is missing, the script will immediately throw a `FileNotFoundError`.
* **How to fix:** Simply copy the existing `experiment.xenium` file in 
`Xenium-Align-UM/Dataset/output-XETG00126_0010207_f59_20240214_210015`

#### 2. The OME-TIFF Morphology Image
* **Missing File:** `morphology_focus.ome.tif` (or `morphology_mip.ome.tif`)
* **Why it is required:** The Xenium reader specifically searches for images with these exact names to load as the coordinate background. 
* **How to fix:** You must rename or copy your existing `TID1_DAPI_scene_5.tif` to `morphology_focus.ome.tif` inside the dataset folder.

#### 3. The Formatted Boundary Data (Parquet)
* **Missing Files:** * `cells.parquet`
  * `cell_boundaries.parquet`
  * `nucleus_boundaries.parquet`
* **Why they are required:** These files contain the X/Y vertices for every cell and nucleus polygon. Step 3 relies on these polygons to calculate overlaps and intersections with the cellpose segmentation performed in Step 2. 
* **CosMx Equivalent:** You have this data in your CosMx polygon `.csv` files, but it must be translated and saved into the `.parquet` format with specific column headers (`cell_id`, `vertex_x`, `vertex_y`).

#### 4. The Transcript and Expression Matrices
* **Missing Files:** * `transcripts.parquet`
  * `cell_feature_matrix.h5`
* **Why they are required:** `transcripts.parquet` holds the X/Y locations of individual RNA transcripts, and the `.h5` file acts as the gene expression count matrix. The `spatialdata_io` library will refuse to build the spatial object if these are missing.
* **CosMx Equivalent:** This corresponds to your CosMx `tx_file.csv` and `exprMat_file.csv`. They must be converted into `.parquet` and HDF5 (`.h5`) formats respectively.

---

### Summary of Actions Required Before Step 3

If you are adapting CosMx data to this pipeline, you cannot run Step 3 directly. You must first:
1. Run a **format translator script** to convert your CosMx `.csv` files into the required `experiment.xenium`, `.parquet`, and `.h5` files.
2. Rename/copy your DAPI `.tif` image to `morphology_focus.ome.tif` inside the target directory.
3. Ensure the output coordinates from Step 2 (Cellpose segmentation) successfully generated the `_H&E_label_location_save.csv` file. 

Once your `Dataset` directory perfectly mirrors the file structure of the standard 10x Genomics Xenium output (like the provided Kidney sample), Step 3 will execute successfully.