import pandas as pd
import h5py
import numpy as np
import json

def main():
    dataset_dir = "../Dataset/"
    
    # 1. File Paths
    cosmx_meta = dataset_dir + "ECSL7731_SLLLYT1D1_metadata_file.csv"
    cosmx_poly = dataset_dir + "ECSL7731_SLLLYT1D1-polygons.csv"
    
    print("Reading CosMx files...")
    df_meta = pd.read_csv(cosmx_meta)
    df_poly = pd.read_csv(cosmx_poly)
    
    # 2. Convert Metadata to Xenium cells.csv.gz
    print("Translating metadata to cells.csv.gz...")
    df_cells = pd.DataFrame({
        'cell_id': df_meta['cell_ID'],
        'x_centroid': df_meta['CenterX_global_px'],
        'y_centroid': df_meta['CenterY_global_px']
    })
    df_cells.to_csv(dataset_dir + "cells.csv.gz", index=False, compression='gzip')

    # 3. Convert Polygons to Xenium cell_boundaries.csv.gz
    print("Translating polygons to cell_boundaries.csv.gz...")
    df_bounds = pd.DataFrame({
        'cell_id': df_poly['cellID'],
        'vertex_x': df_poly['x_global_px'],
        'vertex_y': df_poly['y_global_px']
    })
    df_bounds.to_csv(dataset_dir + "cell_boundaries.csv.gz", index=False, compression='gzip')

    # 4. Create dummy cell_feature_matrix.h5
    print("Generating dummy cell_feature_matrix.h5...")
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

    # 5. Create dummy experiment.xenium
    print("Generating dummy experiment.xenium...")
    dummy_exp = {
        "major_version": 1,
        "minor_version": 0,
        "pixel_size": 0.12
    }
    with open(dataset_dir + "experiment.xenium", "w") as f:
        json.dump(dummy_exp, f)

    print("\n✅ Success! Your CosMx data has been successfully disguised as Xenium data.")

if __name__ == "__main__":
    main()