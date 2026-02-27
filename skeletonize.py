import cv2
import numpy as np
from skimage.morphology import skeletonize
import os, sys

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
        r[a == 0] = 255
        g[a == 0] = 255
        b[a == 0] = 255
        bg = cv2.merge([b, g, r])
    elif len(img.shape) == 3 and img.shape[2] == 3:
        bg = img
    else:
        bg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # ------------------------ 3) Gray ------------------------
    gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)

    # ------------------------ 4) Detect walls (Otsu) ------------------------
    _, bin_img = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # If walls are dark (usual case)
    walls = (bin_img == 0)

    # If result looks inverted, swap to:
    # walls = (bin_img == 255)

    # ------------------------ 5) Thicken walls ------------------------
    kernel = np.ones((5, 5), np.uint8)
    walls_thick = cv2.dilate(walls.astype(np.uint8), kernel, iterations=2).astype(bool)

    # ------------------------ 6) BUILD TRUE WALKABLE REGION ------------------------
    open_space = (~walls_thick).astype(np.uint8)

    h, w = open_space.shape
    ff = open_space.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)

    cv2.floodFill(ff, mask, (0, 0), 2)

    walk_filled = (ff == 1)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
    walk_filled.astype(np.uint8), connectivity=8
    )

    areas = stats[:, cv2.CC_STAT_AREA]

    # ignore background (label 0)
    min_area = int(walk_filled.size * 0.001)  # 0.1% of image size
    valid = np.where(areas >= min_area)[0]
    valid = valid[valid != 0]

    walk_filled = np.isin(labels, valid)

    # ------------------------ 7) Skeleton ------------------------
    skel = skeletonize(walk_filled).astype(np.uint8)

    # ------------------------ 8) Save ------------------------
    skel_rgb = np.full((skel.shape[0], skel.shape[1], 3), 255, dtype=np.uint8)
    skel_rgb[skel == 1] = (206, 130, 49)

    cv2.imwrite(f"{out_prefix}_sk.png", skel_rgb)
    # cv2.imwrite(f"{out_prefix}_bw.png", (walk_filled * 255).astype(np.uint8))
    # cv2.imwrite(f"{out_prefix}_walls.png", (walls_thick.astype(np.uint8) * 255))

    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    color[skel == 1] = (0, 0, 255)
    cv2.imwrite(f"{out_prefix}_overlay.png", color)

    # print(
    #     f"[OK] Saved {out_prefix}_bw.png, {out_prefix}_walls.png, "
    #     f"{out_prefix}_sk.png, {out_prefix}_overlay.png"
    # )
    print(
    f"[OK] Saved {out_prefix}_sk.png and {out_prefix}_overlay.png"
)

# ------------------------ CLI ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skeletonize.py <image_path> [out_prefix]")
        sys.exit(1)

    fp = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) >= 3 else "result"
    process(fp, prefix)