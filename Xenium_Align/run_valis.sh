#!/bin/bash
# Run VALIS registration inside the Singularity container

module load singularity

BASE_DIR="/nfs/turbo/umms-drjieliu/usr/yctao/VALIS"
SRC_DIR="${BASE_DIR}/my_data"
DST_DIR="${BASE_DIR}/my_data_outputs_test"
HE_IMAGE="he_image.tif"
DAPI_IMAGE="dapi_image.tif"

singularity exec /nfs/turbo/umms-drjieliu/usr/yctao/VALIS/valis-wsi_1.0.4.sif \
    python3 run_valis.py \
        --base_dir   "${BASE_DIR}" \
        --src_dir    "${SRC_DIR}" \
        --dst_dir    "${DST_DIR}" \
        --he_image   "${HE_IMAGE}" \
        --dapi_image "${DAPI_IMAGE}"