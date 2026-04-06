import os
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from valis import registration
import tifffile


def set_tiff_resolution(path, um_per_px):
    """Convert µm/px to px/cm and write to TIFF XResolution/YResolution tag."""
    px_per_cm = 10000.0 / um_per_px   # 1 cm = 10000 µm
    img = tifffile.imread(path)
    print(img.ndim)
    tifffile.imwrite(
        path, img,
        resolution=(px_per_cm, px_per_cm),
        resolutionunit=tifffile.RESUNIT.CENTIMETER,
        photometric="rgb" if img.ndim == 3 else "minisblack",
    )
    print(f"Set resolution {um_per_px} µm/px on {os.path.basename(path)}")


def load_for_display(path, max_size=2000):
    """Read image with pyvips (supports LZW ome.tiff), resize, return float32 RGB."""
    import pyvips
    img = pyvips.Image.new_from_file(path, access="sequential")
    scale = min(max_size / img.width, max_size / img.height, 1.0)
    if scale < 1.0:
        img = img.resize(scale)
    arr = np.ndarray(buffer=img.write_to_memory(),
                     dtype=np.uint8,
                     shape=(img.height, img.width, img.bands))
    arr = arr.astype(np.float32) / 255.0
    if arr.shape[2] == 1:
        arr = np.concatenate([arr] * 3, axis=2)
    elif arr.shape[2] == 4:
        arr = arr[:, :, :3]
    return arr


def find_registered(registered_slide_dst_dir, slide_name):
    """Find a registered tif file matching slide_name in registered_slide_dst_dir."""
    for f in os.listdir(registered_slide_dst_dir):
        if slide_name in f and (f.endswith(".tif") or f.endswith(".tiff")):
            return os.path.join(registered_slide_dst_dir, f)
    return None


def main(args):
    SRC_DIR    = args.src_dir
    DST_DIR    = args.dst_dir
    HE_IMAGE   = args.he_image
    DAPI_IMAGE = args.dapi_image

    # ── Set TIFF resolution metadata (VALIS reads from tags) ─────────────────
    set_tiff_resolution(os.path.join(SRC_DIR, HE_IMAGE),   0.1721)
    set_tiff_resolution(os.path.join(SRC_DIR, DAPI_IMAGE), 0.96)

    # ── Run registration ──────────────────────────────────────────────────────
    registrar = registration.Valis(
        src_dir=SRC_DIR,
        dst_dir=DST_DIR,
        check_for_reflections=True,
        crop="reference",
        reference_img_f=HE_IMAGE,
        align_to_reference=True,
        non_rigid_registrar_cls=None,
    )

    rigid_registrar, non_rigid_registrar, errors = registrar.register()

    print("Registration errors:", errors)

    # ── Save registered slides ────────────────────────────────────────────────
    registered_slide_dst_dir = os.path.join(DST_DIR, "registered_slides")
    registrar.warp_and_save_slides(registered_slide_dst_dir)
    print(f"Registered slides saved to: {registered_slide_dst_dir}")

    # ── Visualization ─────────────────────────────────────────────────────────
    he_stem   = os.path.splitext(HE_IMAGE)[0]
    dapi_stem = os.path.splitext(DAPI_IMAGE)[0]

    he_orig   = os.path.join(SRC_DIR, HE_IMAGE)
    dapi_orig = os.path.join(SRC_DIR, DAPI_IMAGE)

    he_reg   = find_registered(registered_slide_dst_dir, he_stem)
    dapi_reg = find_registered(registered_slide_dst_dir, dapi_stem)

    if he_reg is None or dapi_reg is None:
        print("WARNING: Could not find registered slides for visualization.")
    else:
        he_orig_img   = load_for_display(he_orig)
        dapi_orig_img = load_for_display(dapi_orig)
        he_reg_img    = load_for_display(he_reg)
        dapi_reg_img  = load_for_display(dapi_reg)

        from skimage.transform import resize as sk_resize

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle("VALIS Registration: H&E <-> DAPI", fontsize=16)

        # Row 0: before registration
        axes[0, 0].imshow(he_orig_img);   axes[0, 0].set_title("H&E (original)")
        axes[0, 1].imshow(dapi_orig_img); axes[0, 1].set_title("DAPI (original)")
        overlay_before = he_orig_img.copy()
        h, w = he_orig_img.shape[:2]
        d_resized = sk_resize(dapi_orig_img, (h, w), anti_aliasing=True)
        overlay_before[:, :, 1] = np.clip(overlay_before[:, :, 1] + 0.4 * d_resized[:, :, 0], 0, 1)
        axes[0, 2].imshow(overlay_before); axes[0, 2].set_title("Overlay (before)")

        # Row 1: after registration
        axes[1, 0].imshow(he_reg_img);   axes[1, 0].set_title("H&E (registered)")
        axes[1, 1].imshow(dapi_reg_img); axes[1, 1].set_title("DAPI (registered)")
        overlay_after = he_reg_img.copy()
        h2, w2 = he_reg_img.shape[:2]
        d_reg_resized = sk_resize(dapi_reg_img, (h2, w2), anti_aliasing=True)
        overlay_after[:, :, 1] = np.clip(overlay_after[:, :, 1] + 0.4 * d_reg_resized[:, :, 0], 0, 1)
        axes[1, 2].imshow(overlay_after); axes[1, 2].set_title("Overlay (after)")

        for ax in axes.flat:
            ax.axis("off")

        plt.tight_layout()
        out_png = os.path.join(DST_DIR, "registration_visualization.png")
        plt.savefig(out_png, dpi=150, bbox_inches="tight")
        print(f"Visualization saved to: {out_png}")
        plt.close()

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run VALIS registration on H&E and DAPI images.")
    parser.add_argument("--base_dir",   required=True,            help="Base directory")
    parser.add_argument("--src_dir",    required=True,            help="Source directory containing input images")
    parser.add_argument("--dst_dir",    required=True,            help="Destination directory for outputs")
    parser.add_argument("--he_image",   default="he_image.tif",   help="H&E image filename in the source directory")
    parser.add_argument("--dapi_image", default="dapi_image.tif", help="DAPI image filename in the source directory")
    main(parser.parse_args())
