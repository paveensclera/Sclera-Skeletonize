# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

An SVG routing pipeline that converts PNG floor plan images into navigable SVG path graphs. The output SVGs are consumed by `visualize.js` to power click-to-route pathfinding (Dijkstra's) in a web UI.

## Build & Run

**Build Docker image:**
```bash
docker build -t autopaths_pipeline .
```

**Run as a FastAPI server (default):**
```bash
docker run --rm -p 8000:8000 autopaths_pipeline
# POST /process  — multipart file upload, returns image/svg+xml
```

**Override entrypoint to run the original batch pipeline on a directory of PNGs:**
```bash
docker run --rm -v $(pwd)/pngs:/data -v $(pwd)/outputs:/output \
  --entrypoint bash autopaths_pipeline /app/pipeline.sh /data
```

**Run individual pipeline steps locally** (requires Python deps + autotrace + potrace installed):
```bash
# Step 1 – skeletonize
python3 skeletonize.py pngs/test.png outputs/test/test

# Step 2 – autotrace (produces _sk.svg from _sk.png)
autotrace outputs/test/test_sk.png -centerline -output-file outputs/test/test_sk.svg

# Step 3 – linearize
python3 linearize.py outputs/test/test_sk.svg outputs/test/test_sklin.svg

# Step 4 – potrace + merge
magick outputs/test/test.png -threshold 99% outputs/test/test.pbm
potrace outputs/test/test.pbm -s -o outputs/test/test.svg
./merge.sh outputs/test/test.svg outputs/test/test_sklin.svg outputs/merged/test_merged.svg
```

**Install Python dependencies:**
```bash
pip install -r requirements.txt
```

## Pipeline Architecture

Four sequential steps orchestrated by `pipeline.sh`:

1. **`skeletonize.py`** — Loads PNG, applies Otsu thresholding to detect walls, dilates walls 2 iterations, extracts medial-axis skeleton via scikit-image. Outputs `_sk.png` (skeleton), `_overlay.png` (debug overlay), and raw binarized `_sk.png` for autotrace. Includes aggressive GC for large images.

2. **autotrace** (external binary built from source in Docker at commit `2d0b8cce`) — Traces the skeleton PNG into centerline SVG curves (`_sk.svg`). Pinned to a specific commit to avoid regressions.

3. **`linearize.py`** — Post-processes autotrace SVG: snaps nearby path endpoints together using a KD-tree (THRESHOLD=20px snap radius), reduces collinear points (SIMPLIFY_TOL=2px), but preserves intersection points to maintain path connectivity. Outputs `_sklin.svg`.

4. **`merge.sh`** + potrace — Separately runs potrace (area-fill tracing) on the original PNG, then merges the potrace SVG with the linearized autotrace SVG into a final `_merged.svg` with a white background.

## Key Parameters

- `THRESHOLD = 20` (px) — snap radius for endpoint clustering in linearize.py
- `SIMPLIFY_TOL = 2` (px) — collinearity tolerance for path simplification
- Min path length: 30px (shorter paths are discarded as noise)
- Connected component filter: < 0.1% of image area is discarded
- ImageMagick memory limits in Dockerfile: 16GB memory, 64GB disk (for large floor plans)

## Output Structure

```
outputs/
  merged/               ← Final SVGs consumed by visualize.js
  <image_name>/         ← Intermediates per input image
    *_sk.png            ← Skeleton
    *_overlay.png       ← Debug overlay
    *_sk.svg            ← Autotrace output
    *_sklin.svg         ← Linearized
    *.pbm               ← Potrace working file
  autopaths_*.log       ← Per-run timing + memory metrics
```

## Web Visualization

`visualize.js` + `index.html` form a routing demo:
- Parses merged SVGs to build a path graph (nodes = endpoints/intersections, edges = path segments)
- Click-to-route via Dijkstra's algorithm
- Orange polyline = computed route; green/red circles = start/end markers

## Docker Details

The Dockerfile clones autotrace from GitHub at a pinned commit and builds it from source (C build with autotools). This is intentional — the autotrace package in apt is outdated and produces worse centerlines. The `.dockerignore` prevents local output files from being copied into the build context.
