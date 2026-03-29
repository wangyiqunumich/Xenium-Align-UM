# End-to-End Image Alignment: Nanostring CosMx to Xenium-Align-UM

This tutorial walks through the process of aligning standard H&E tissue images with Nanostring CosMx spatial transcriptomics data using the `Xenium-Align-UM` pipeline. 

Because this pipeline was natively built for 10x Genomics Xenium data, this guide includes the necessary "Step 0" to extract your raw images and safely format your CosMx coordinate data so the pipeline accepts it without requiring complex source-code modifications.

---

## Prerequisites & Folder Structure
Before beginning, ensure your working directory looks like this:
```text
Project_Folder/
├── Xenium_Align/                  # The cloned pipeline repository
│   ├── extract_dapi.py
│   ├── extract_he.py
│   ├── cosmx_to_xenium_translator.py
│   ├── reflect_he.py
│   ├── data_preprocess_check.py
│   ├── data_preprocess_check_no_rotations.py
│   ├── cellpose_image_segmentation.py
│   └── xenium_alignment_for_keypoints.py
└── Dataset/                       # Your data folder
    ├── TID1_scene5_cosmx.tiff     # Raw CosMx multi-channel TIFF
    ├── 01.czi                     # Raw H&E brightfield image
    ├── ECSL7731_SLLLYT1D1_metadata_file.csv # CosMx metadata
    └── ECSL7731_SLLLYT1D1-polygons.csv      # CosMx cell boundaries
```

---

## Step 0: Data Preparation & Disguising CosMx Data

The alignment pipeline uses a strict third-party data reader (`spatialdata_io`). It will crash if it does not see a perfectly formatted 10x Xenium output folder (including specific `.parquet` files, `experiment.xenium`, and `morphology_focus.ome.tif`). 

### 0a. Extract DAPI from CosMx TIFF
The pipeline needs a 2D, single-channel `.tif` for DAPI. Run this to isolate the DAPI channel from your multi-channel CosMx TIFF.
```bash
python extract_dapi.py
```

### 0b. Extract H&E from `.czi`
H&E images are often scanned into proprietary Zeiss `.czi` files. Run this to unpack the brightfield image into a standard `.tif`.
```bash
python extract_he.py
```

### 0c. Disguise CosMx Data as Xenium Data
This translator script bypasses the pipeline's strict format checks by mapping CosMx coordinates to Xenium standards, converting `.csv` files into `.parquet` formats, generating a dummy `experiment.xenium` file and an empty `cell_feature_matrix.h5` matrix, and ensuring your DAPI `.tif` is properly named `morphology_focus.ome.tif`.
```bash
python cosmx_to_xenium_translator.py
```

---

## Step 1: Data Preprocess Check

**Command:**
```bash
nohup python data_preprocess_check.py -sample TID1 -preservation_method ff -data_file_path ../Dataset/ > step1_preprocess.log 2>&1 &
```

**What this does:**
This step verifies the spatial compatibility between your H&E image and the spatial DAPI coordinates. It automatically tests basic 180-degree rotations and Top-Bottom/Left-Right flips by calculating the Mean Squared Error (MSE) between the images to find the best initial alignment.

**Handling Custom Rotations & Reflections:**
* **Reflections:** If your H&E image requires a true mathematical matrix reflection (not just a display tag) prior to running this step, use the included `reflect_he.py` script.
* **90° or 270° Rotations:** The standard script does not dynamically test 90° or 270° rotations because differing aspect ratios (landscape vs. portrait) will cause the pipeline to crash. If your image requires a 90° or 270° rotation, it is best to either:
  1. Edit the image manually (via script or software) to pre-align it. 
  2. Once you have a manually pre-aligned image, simply run **`data_preprocess_check_no_rotations.py`** instead of the standard script to bypass the automated flipping loop while still generating the required configuration files.

**Outputs Generated:**
* **Directory:** `../Dataset/TID1_image_check/`
* **Files Created:** * Visual JPEG overlays for manual alignment verification.
  * `TID1_he_rotate_mse_values.csv`: A crucial configuration file. **Do not delete this.** Step 2 and Step 3 rely on this file to know which mathematical coordinate transformations to apply.

---

## Step 2: H&E Image Segmentation

**Command:**
```bash
nohup python cellpose_image_segmentation.py -sample TID1 -preservation_method ff -data_file_path ../Dataset/ -channel_cellpose 1 -min_size 15 -flow_threshold 0.8 -use_gpu True > step2_segmentation.log 2>&1 &
```

**What this does:**
This step uses Cellpose (or StarDist) AI models to detect the boundaries of every cell nucleus in your H&E image. It reads the `_he_rotate_mse_values.csv` from Step 1 to ensure it extracts the coordinates using the correct spatial orientation. *(Note: `-channel_cellpose 1` targets the primary grayscale channel, which is ideal for extracted DAPI/H&E).*

**Outputs Generated:**
* **Directory:** `../Dataset/` and `../Dataset/TID1_image_check/`
* **Files Created:**
  * Segmentation Masks: Visual confirmation files showing the AI's detected cell boundaries.
  * `TID1_H&E_label_location_save.csv`: A file containing the precise X/Y pixel coordinates of every cell found in the H&E image. This is required for Step 3.

---

## Prerequisites: Required Files for Step 3 (Xenium Alignment)

Before running `xenium_alignment_for_keypoints.py` (Step 3), your `Dataset` folder must be strictly formatted as a standard **10x Genomics Xenium** output directory. 

Because the alignment script uses the `spatialdata_io.xenium()` function to load the dataset, it will **fail** if it only finds raw `.tif` images or raw CosMx `.csv` files. The reader physically cannot parse standard CSVs or raw TIFFs without the accompanying Xenium metadata and parquet structures.

### Current State vs. Required State

**What you currently have:**
* `TID1_DAPI_scene_5.tif` (Raw DAPI image)
* `TID1_HE_scene_5.tif` (Raw H&E image)
* *Various CosMx tabular outputs (e.g., transcript and polygon CSVs)*

**What Step 3 strictly requires:**
To bypass the `spatialdata_io` reader checks, your dataset folder must contain the following specific Xenium-formatted files (which Step 0c handled for you):

#### 1. The Xenium Configuration File
* **Missing File:** `experiment.xenium`
* **Why it is required:** This is the master metadata file. `spatialdata_io` reads this first to determine the physical pixel size and the software version. If this file is missing, the script will immediately throw a `FileNotFoundError`.
* **How to fix:** Simply copy the existing `experiment.xenium` file from a valid Xenium output folder into your Dataset folder.

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

### Summary of Actions Required Before Step 3

If you are adapting CosMx data to this pipeline, you cannot run Step 3 directly. You must first:
1. Run a **format translator script** to convert your CosMx `.csv` files into the required `experiment.xenium`, `.parquet`, and `.h5` files.
2. Rename/copy your DAPI `.tif` image to `morphology_focus.ome.tif` inside the target directory.
3. Ensure the output coordinates from Step 2 (Cellpose segmentation) successfully generated the `TID1_H&E_label_location_save.csv` file. 

Once your `Dataset` directory perfectly mirrors the file structure of the standard 10x Genomics Xenium output, Step 3 will execute successfully.

---

## Step 3: Xenium Alignment for Keypoints

**Command:**
```bash
nohup python xenium_alignment_for_keypoints.py -sample TID1 -preservation_method ff -data_file_path ../Dataset/ -crop_radius_pixel 400 -center_move_pixel 300 -check_cell_num 100 -mip_ome_extract_ratio 0.125 -mip_ome_extract_min 50 -segment_method cellpose -overlap_type overlap_ave -overlap_threshold_ave 0.9 -keypoints_min_num 15 -epoch_num 30 > step3_keypoints.log 2>&1 &
```

**What this does:**
This is the core mathematical alignment step. Now that your Dataset folder contains the required `.parquet` files, the `.ome.tif` images, and the Cellpose coordinates from Step 2, this script calculates the physical geometric overlaps between the H&E cell polygons and the CosMx spatial transcriptomics coordinates. It identifies "keypoints" (matching cellular landmarks) to compute the final spatial transformation matrix.

**Outputs Generated:**
* **Directory:** `../Dataset/` (and runtime logs in your current `Xenium_Align` working directory).
* **Files Created:**
  * `step3_keypoints.log`: Real-time progress (viewable via `tail -f step3_keypoints.log`).
  * Final Transformation Matrices: The output CSV/data files required to perfectly overlay your H&E brightfield image onto your spatial transcriptomics viewer.