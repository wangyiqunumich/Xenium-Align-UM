# Xenium-Align-UM Tutorial

This tutorial guides you through the process of aligning H&E images with Xenium/CosMx DAPI-stained images. The pipeline is designed to handle massive high-resolution images by utilizing GPU acceleration and background processing.

---

## 🛠️ Background Execution Guide (`nohup`)

Because these alignment scripts process extremely large image matrices, they can take hours to complete. It is highly recommended to run them in the background using `nohup` (No Hang Up) so the process continues even if you disconnect from the server.

**How to use `nohup`:**
Add `nohup` to the beginning of your command, and `> step_log.log 2>&1 &` to the end. 
*Example:* `nohup python script.py -args > step_log.log 2>&1 &`

**How to monitor your progress:**
* **View live logs:** `tail -f step_log.log` (Press `Ctrl + C` to exit the live viewer).
* **Check if it's still running:** `ps aux | grep script.py | grep -v grep`
* **Check hardware usage:** `top -u your_username` or `watch -n 2 nvidia-smi` (to monitor GPU memory and utilization).

---

## 📂 Initial Directory Setup

Before running the pipeline, ensure your working directory follows this structure. The input images (both H&E and DAPI) should be placed directly inside the `Dataset/` folder. All executable scripts and helper functions must be located in the `Xenium_Align` folder. 

Additionally, your standard Xenium output folder (which contains the `experiment.xenium` file) should be present in the root directory.

```text
Xenium-Align-UM/
├── Dataset/
│   ├── {sample_name}_HE.tif (or .tiff)
│   └── {sample_name}_DAPI.tif (or .tiff)
│   ├── experiment.xenium
└── Xenium_Align/
    ├── extract_dapi.py
    ├── extract_he.py
    ├── reflect_he.py
    ├── data_preprocess_check.py
    ├── cellpose_image_segmentation.py
    ├── xenium_alignment_for_keypoints.py
    ├── alignment_data_process.py
    ├── graph_build.py
    ├── stardist_image_segmentation.py
    └── util_function.py
```

---

## Step 0: Image Preparation (Optional)

If your raw data is bundled in complex formats (like `.ome.tif` or large vendor-specific exports) or requires reflection, complete these sub-steps before starting the alignment.

### Step 0.1: Extracting Images
Use the provided extraction scripts to pull standard `.tif` or `.tiff` images from your raw data. Place the resulting files directly into the `Dataset/` folder.
* **Extract DAPI:**
  ```bash
  python extract_dapi.py -input raw_data.ome.tif -output ../Dataset/{sample_name}_DAPI.tif
  ```
* **Extract H&E:**
  ```bash
  python extract_he.py -input raw_data.svs -output ../Dataset/{sample_name}_HE.tif
  ```

### Step 0.2: Manual Image Reflection
Our modified pipeline handles rotations automatically in Step 1, but **reflections (flips)** must be done manually if the tissue was mounted backward. If your H&E image appears mirrored compared to your DAPI image, run the reflection script:
```bash
python reflect_he.py -input ../Dataset/{sample_name}_HE.tif -output ../Dataset/{sample_name}_HE_reflected.tif
```
*(Make sure to rename the final file to match your standard `{sample_name}_HE.tif` before proceeding!)*

---

## Step 1: Data Preprocess Check

This step automatically checks the 4 possible rotations (0°, 90°, 180°, 270°) of the H&E image against the DAPI image by calculating the Mean Squared Error (MSE) at a low resolution. It then saves the best alignment and generates preview thumbnails.

**Standard Command:**
```bash
python data_preprocess_check.py -sample {sample_name} -data_file_path ../Dataset/
```

**Nohup Command:**
```bash
nohup python data_preprocess_check.py -sample {sample_name} -data_file_path ../Dataset/ > step1_preprocess.log 2>&1 &
```

### 📁 Expected Output After Step 1
Upon successful completion, a new folder named `{sample_name}_image_check` will be created inside the `Xenium_Align` directory:

```text
Xenium_Align/
├── {sample_name}_image_check/
│   ├── {sample_name}_HE_image.jpg
│   ├── {sample_name}_DAPI_image.jpg
│   └── {sample_name}_he_rotate_mse_values.csv
```
*Note: Verify the `.jpg` previews manually to ensure the tissue orientation matches before proceeding to Step 2!*

---

## Step 2: Cellpose Image Segmentation

This step uses the Cellpose deep learning model to detect and mask every cell nucleus in the image. **A GPU is highly recommended for this step.**

* `channel_cellpose`: 0 for grayscale (extracted DAPI), 1 for red, 2 for green, 3 for blue.
* `-use_gpu True`: Forces the script to use the NVIDIA GPU to drastically reduce compute time.

**Standard Command:**
```bash
python cellpose_image_segmentation.py -sample {sample_name} -preservation_method ff -data_file_path ../Dataset/ -channel_cellpose 0 -min_size 15 -flow_threshold 0.8 -use_gpu True
```

**Nohup Command:**
```bash
nohup python cellpose_image_segmentation.py -sample {sample_name} -preservation_method ff -data_file_path ../Dataset/ -channel_cellpose 0 -min_size 15 -flow_threshold 0.8 -use_gpu True > step2_cellpose.log 2>&1 &
```

### 📁 Expected Output After Step 2
A new folder containing the coordinate arrays and segmentation previews will be generated:
```text
Xenium_Align/
├── {sample_name}_cellpose_channel_cellpose0_flow_threshold0.8_min_size15/
│   ├── ...cell_num.csv
│   ├── ...label_mark_scale.jpg
│   └── ...tif_image_segmented_cellpose.csv (Massive matrix file)
```

---

## Step 3: Keypoints Generation

The final step takes the massive cell mask arrays from Step 2 and hunts for corresponding keypoints between the H&E and DAPI images to establish the final spatial alignment matrix. *(Note: This step is CPU-only and does not use the GPU flag).*

**Standard Command:**
```bash
python xenium_alignment_for_keypoints.py -sample {sample_name} -preservation_method ff -data_file_path ../Dataset/ -crop_radius_pixel 400 -center_move_pixel 300 -check_cell_num 100 -mip_ome_extract_ratio 0.125 -mip_ome_extract_min 50 -segment_method cellpose -overlap_type overlap_ave -overlap_threshold_ave 0.9 -keypoints_min_num 15 -epoch_num 30
```

**Nohup Command:**
```bash
nohup python xenium_alignment_for_keypoints.py -sample {sample_name} -preservation_method ff -data_file_path ../Dataset/ -crop_radius_pixel 400 -center_move_pixel 300 -check_cell_num 100 -mip_ome_extract_ratio 0.125 -mip_ome_extract_min 50 -segment_method cellpose -overlap_type overlap_ave -overlap_threshold_ave 0.9 -keypoints_min_num 15 -epoch_num 30 > step3_keypoints.log 2>&1 &
```

### 📁 Expected Output After Step 3
Once this successfully completes, your keypoints will be fully generated and saved, ready for downstream analysis or visualization.