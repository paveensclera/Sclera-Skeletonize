#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo "Usage: ./pipeline.sh <png_directory>"
  exit 1
fi

INPUT_DIR="$1"
BASE_OUT="outputs"
mkdir -p "$BASE_OUT"

run_step() {
  STEP_NAME="$1"
  shift

  echo "$STEP_NAME..."
  START=$(date +%s%3N)

  "$@"

  END=$(date +%s%3N)
  DURATION_MS=$((END - START))
  DURATION=$(awk "BEGIN { printf \"%.1f\", $DURATION_MS/1000 }")

  echo "✓ Done (${DURATION} sec)"
  echo
}

for img in "$INPUT_DIR"/*.png; do
  name=$(basename "$img" .png)
  OUTDIR="$BASE_OUT/$name"
  mkdir -p "$OUTDIR"

  echo "===================================="
  echo "Processing: $name"
  echo

  cp "$img" "$OUTDIR/$name.png"

  run_step "Step 1/4 Skeletonize" \
    python skeletonize.py "$OUTDIR/$name.png" "$OUTDIR/$name"

  run_step "Step 2/4 Autotrace Skeleton SVG" \
    env MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(pwd)/$OUTDIR:/app" \
    autotrace \
    /app/${name}_sk.png -centerline \
    -output-file /app/${name}_sk.svg

  run_step "Step 3/4 Linearize" \
    python linearize.py \
    "$OUTDIR/${name}_sk.svg" \
    "$OUTDIR/${name}_sklin.svg"

  run_step "Step 4/4 Potrace + Merge" \
    env MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(pwd):/app" \
    -w /app \
    potracer \
    "magick $OUTDIR/$name.png -threshold 99% $OUTDIR/$name.pbm && \
     potrace $OUTDIR/$name.pbm -s -o $OUTDIR/$name.svg && \
     ./merge.sh $OUTDIR/$name.svg $OUTDIR/${name}_sklin.svg $OUTDIR/${name}_merged.svg"

  echo "✔ Finished: ${name}_merged.svg"
  echo
done

echo "All files processed."