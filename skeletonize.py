import cv2
import numpy as np
from skimage.morphology import skeletonize
import os, sys
import gc

def process(fp, out_prefix="result"):
    # ------------------------ 1) Load safely ------------------------
    if not os.path.exists(fp):
        raise FileNotFoundError(f"File not found: {fp}")

    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to load image: {fp}")

    # ------------------------ 2) Handle alpha ------------------------
    if len(img.shape) == 3 and img.shape[2] == 4:
        b, g, r, a = cv2.split(img)
        bg = cv2.merge([b, g, r])
        alpha_mask = (a > 0)
        del a
    elif len(img.shape) == 3 and img.shape[2] == 3:
        bg = img
        alpha_mask = np.ones(bg.shape[:2], dtype=bool)
    else:
        bg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        alpha_mask = np.ones(bg.shape[:2], dtype=bool)

    del img
    gc.collect()

    # ------------------------ 3) Gray ------------------------
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    del bg
    gc.collect()

    # ------------------------ 4) Detect walls (Otsu) ------------------------
    _, bin_img = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    del gray
    gc.collect()

    walls = (bin_img == 0)
    del bin_img

    # Transparent pixels are treated as walls
    walls |= (~alpha_mask)
    del alpha_mask
    gc.collect()

    # ------------------------ 5) Thicken walls ------------------------
    kernel = np.ones((5, 5), np.uint8)

    # reuse same variable (avoid extra array)
    walls = cv2.dilate(
        walls.astype(np.uint8, copy=False),
        kernel,
        iterations=2
    ).astype(bool)

    # ------------------------ 6) BUILD TRUE WALKABLE REGION ------------------------
    walk_filled = ~walls
    del walls
    gc.collect()

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        walk_filled.astype(np.uint8, copy=False), connectivity=8
    )

    areas = stats[:, cv2.CC_STAT_AREA]

    min_area = int(walk_filled.size * 0.001)
    valid = np.where(areas >= min_area)[0]
    valid = valid[valid != 0]

    walk_filled = np.isin(labels, valid)

    # free heavy stuff ASAP
    del labels
    del stats
    del areas
    del valid
    gc.collect()

    # ------------------------ 7) Skeleton ------------------------
    skel = skeletonize(walk_filled).astype(np.uint8)
    del walk_filled
    gc.collect()

    # ------------------------ 8) Save ------------------------
    skel_rgb = np.full((skel.shape[0], skel.shape[1], 3), 255, dtype=np.uint8)
    skel_rgb[skel == 1] = (206, 130, 49)

    cv2.imwrite(f"{out_prefix}_sk.png", skel_rgb)

    # reuse grayscale instead of recomputing (memory-safe)
    color = skel_rgb.copy()
    color[:] = (255, 255, 255)
    color[skel == 1] = (0, 0, 255)

    cv2.imwrite(f"{out_prefix}_overlay.png", color)

    print(f"[OK] Saved {out_prefix}_sk.png and {out_prefix}_overlay.png")


# ------------------------ CLI ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skeletonize.py <image_path> [out_prefix]")
        sys.exit(1)

    fp = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) >= 3 else "result"
    process(fp, prefix)