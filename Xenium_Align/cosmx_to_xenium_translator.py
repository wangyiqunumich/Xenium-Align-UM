import pandas as pd
import h5py
import numpy as np
import json
import os

def main():
    dataset_dir = "../Dataset/"
    
    cosmx_meta = os.path.join(dataset_dir, "ECSL7731_SLLLYT1D1_metadata_file.csv")
    cosmx_poly = os.path.join(dataset_dir, "ECSL7731_SLLLYT1D1-polygons.csv")
    
    df_meta = pd.read_csv(cosmx_meta)
    df_poly = pd.read_csv(cosmx_poly)
    
    # 1. Create a unique raw ID based on FOV and Cell ID
    df_meta['raw_id'] = df_meta['fov'].astype(str) + "_" + df_meta['cell_ID'].astype(str)
    df_poly['raw_id'] = df_poly['fov'].astype(str) + "_" + df_poly['cellID'].astype(str)

    # 2. Clean metadata duplicates
    df_meta = df_meta.drop_duplicates(subset=['raw_id'])

    # 3. Clean polygons: spatialdata_io drops shapes with < 3 vertices. We must drop them first.
    poly_counts = df_poly['raw_id'].value_counts()
    valid_poly_ids = poly_counts[poly_counts >= 3].index
    df_poly = df_poly[df_poly['raw_id'].isin(valid_poly_ids)]

    # 4. Strict Intersection
    common_ids = sorted(list(set(df_meta['raw_id']).intersection(set(df_poly['raw_id']))))
    
    df_meta = df_meta[df_meta['raw_id'].isin(common_ids)].copy()
    df_poly = df_poly[df_poly['raw_id'].isin(common_ids)].copy()

    # 5. BULLETPROOF ID MAPPING: Map to zero-padded sequential strings (e.g., "00000001")
    # This completely overrides pandas string-sorting quirks during the spatialdata_io groupby.
    id_mapping = {raw_id: f"{i:08d}" for i, raw_id in enumerate(common_ids)}
    
    df_meta['cell_id'] = df_meta['raw_id'].map(id_mapping)
    df_poly['cell_id'] = df_poly['raw_id'].map(id_mapping)

    # 6. Enforce strict sorting on the new IDs
    df_meta = df_meta.sort_values('cell_id').reset_index(drop=True)
    sorted_new_ids = df_meta['cell_id'].tolist()

    print(f"Translating {len(sorted_new_ids)} cleanly matched cells...")

    # --- Generate Files ---
    
    # cells.parquet
    df_cells = pd.DataFrame({
        'cell_id': df_meta['cell_id'],
        'x_centroid': df_meta['CenterX_global_px'],
        'y_centroid': df_meta['CenterY_global_px'],
        'transcript_counts': 100,
        'control_probe_counts': 0,
        'control_codeword_counts': 0,
        'unassigned_codeword_counts': 0,
        'deprecated_codeword_counts': 0,
        'total_counts': 100,
        'cell_area': 100.0,
        'nucleus_area': 50.0
    })
    df_cells.to_parquet(os.path.join(dataset_dir, "cells.parquet"), index=False)

    # boundaries.parquet
    df_bounds = pd.DataFrame({
        'cell_id': df_poly['cell_id'],
        'vertex_x': df_poly['x_global_px'],
        'vertex_y': df_poly['y_global_px']
    })
    df_bounds.to_parquet(os.path.join(dataset_dir, "cell_boundaries.parquet"), index=False)
    df_bounds.to_parquet(os.path.join(dataset_dir, "nucleus_boundaries.parquet"), index=False)

    # transcripts.parquet
    df_transcripts = pd.DataFrame({
        'transcript_id': [1],
        'cell_id': [sorted_new_ids[0]],
        'overlapped_nucleus': [1],
        'feature_name': ['dummy_gene'],
        'x_location': [0.0],
        'y_location': [0.0],
        'z_location': [0.0],
        'qv': [40.0],
        'fov_name': ['A1']
    })
    df_transcripts.to_parquet(os.path.join(dataset_dir, "transcripts.parquet"), index=False)

    # cell_feature_matrix.h5
    N = len(sorted_new_ids)
    cell_ids_bytes = np.array(sorted_new_ids, dtype='S')
    
    with h5py.File(os.path.join(dataset_dir, 'cell_feature_matrix.h5'), 'w') as f:
        matrix = f.create_group('matrix')
        matrix.create_dataset('barcodes', data=cell_ids_bytes)
        matrix.create_dataset('data', data=np.array([], dtype='f4'))
        matrix.create_dataset('indices', data=np.array([], dtype='i4'))
        matrix.create_dataset('indptr', data=np.zeros(N + 1, dtype='i4'))
        matrix.create_dataset('shape', data=np.array([1, N], dtype='i4'))
        
        features = matrix.create_group('features')
        features.create_dataset('id', data=np.array(['dummy_gene'], dtype='S'))
        features.create_dataset('name', data=np.array(['dummy_gene'], dtype='S'))
        features.create_dataset('feature_type', data=np.array(['Gene Expression'], dtype='S'))
        features.create_dataset('genome', data=np.array(['dummy_genome'], dtype='S'))

    # experiment.xenium
    dummy_exp = {
        "major_version": 1,
        "minor_version": 0,
        "pixel_size": 0.12,
        "analysis_sw_version": "xenium-1.6.0",
        "region_name": "region_1"
    }
    with open(os.path.join(dataset_dir, "experiment.xenium"), "w") as f:
        json.dump(dummy_exp, f)

if __name__ == "__main__":
    main()