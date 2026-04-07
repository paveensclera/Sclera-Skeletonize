#!/bin/bash

set -e

if [ "$#" -lt 1 ]; then
  echo "Usage: ./pipeline.sh <png_directory>"
  exit 1
fi

INPUT_DIR="$1"
BASE_OUT="test_outputs"
mkdir -p "$BASE_OUT"

MERGED_DIR="$BASE_OUT/merged"
mkdir -p "$MERGED_DIR"

STRUCT_LOG="$BASE_OUT/autopaths_$(date +%Y%m%d_%H%M%S).log"

{
  echo "========= SYSTEM INFO ========="

  CPU_INFO=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs)
  [ -z "$CPU_INFO" ] && CPU_INFO=$(uname -p 2>/dev/null)

  CORES=$(getconf _NPROCESSORS_ONLN 2>/dev/null)

  RAM=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{printf "%.1fGB", $2/1024/1024}')

  echo "[CPU] ${CPU_INFO:-unknown}"
  echo "[CORES] ${CORES:-unknown}"
  echo "[RAM] ${RAM:-unknown}"
  echo "[OS] $(uname -sr)"
  echo "================================"
  echo
} >> "$STRUCT_LOG"

TOTAL_RUN_START=$(date +%s%3N)
TOTAL_MAPS=0

run_step() {
  STEP_NAME="$1"
  shift

  echo "$STEP_NAME..." >&2
  START=$(date +%s%3N)

  TMP_LOG=$(mktemp)

  /usr/bin/time -v "$@" 2> "$TMP_LOG" 1>&2

  END=$(date +%s%3N)
  DURATION_MS=$((END - START))
  DURATION=$(awk "BEGIN { printf \"%.1f\", $DURATION_MS/1000 }")

  PEAK_KB=$(grep "Maximum resident set size" "$TMP_LOG" | awk '{print $6}')
  PEAK_MB=$(awk "BEGIN { printf \"%.1f\", $PEAK_KB/1024 }")

  rm "$TMP_LOG"

  echo "✓ Done (${DURATION} sec | ${PEAK_MB} MB)" >&2
  echo >&2

  echo "$DURATION|$PEAK_MB"
}

shopt -s nullglob
for img in "$INPUT_DIR"/*.png; do
  name=$(basename "$img" .png)
  OUTDIR="$BASE_OUT/$name"

  if [ -f "$MERGED_DIR/${name}_merged.svg" ]; then
    echo "Skipping $name (already processed)"
    echo
    continue
  fi

  [ -d "$OUTDIR" ] || mkdir "$OUTDIR"

  echo "===================================="
  echo "Processing: $name"
  echo

  cp "$img" "$OUTDIR/$name.png"

  # IMAGE INFO
  DIMENSIONS=$(python -c "from PIL import Image; Image.MAX_IMAGE_PIXELS=None;
import sys;
try:
    im=Image.open('$img');
    print(f'{im.width}x{im.height}')
except:
    print('unknown')")

  FILESIZE_BYTES=$(wc -c < "$img")
  FILESIZE_MB=$(awk "BEGIN { printf \"%.1f\", $FILESIZE_BYTES/1024/1024 }")

  MAP_START=$(date +%s%3N)

  # STEP 1
  res1=$(run_step "Step 1/4 Skeletonize" \
    python skeletonize.py "$OUTDIR/$name.png" "$OUTDIR/$name")
  t1=$(echo $res1 | cut -d'|' -f1)
  m1=$(echo $res1 | cut -d'|' -f2)

  # STEP 2
  res2=$(run_step "Step 2/4 Autotrace Skeleton SVG" \
    env MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(pwd)/$OUTDIR:/app" \
    autotracer \
    /app/${name}_sk.png -centerline \
    -output-file /app/${name}_sk.svg)
  t2=$(echo $res2 | cut -d'|' -f1)
  m2=$(echo $res2 | cut -d'|' -f2)

  # STEP 3
  res3=$(run_step "Step 3/4 Linearize" \
    python linearize.py \
    "$OUTDIR/${name}_sk.svg" \
    "$OUTDIR/${name}_sklin.svg")
  t3=$(echo $res3 | cut -d'|' -f1)
  m3=$(echo $res3 | cut -d'|' -f2)

  # STEP 4
  res4=$(run_step "Step 4/4 Potrace + Merge" \
    env MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(pwd):/app" \
    -w /app \
    potracer \
    "magick $OUTDIR/$name.png -threshold 99% $OUTDIR/$name.pbm && \
     potrace $OUTDIR/$name.pbm -s -o $OUTDIR/$name.svg && \
     ./merge.sh $OUTDIR/$name.svg $OUTDIR/${name}_sklin.svg $MERGED_DIR/${name}_merged.svg")
  t4=$(echo $res4 | cut -d'|' -f1)
  m4=$(echo $res4 | cut -d'|' -f2)

  # PEAK RAM across steps
  MAP_PEAK=$(printf "%s\n%s\n%s\n%s\n" $m1 $m2 $m3 $m4 | sort -nr | head -1)

  MAP_END=$(date +%s%3N)
  MAP_TOTAL_MS=$((MAP_END - MAP_START))
  MAP_TOTAL=$(awk "BEGIN { printf \"%.1f\", $MAP_TOTAL_MS/1000 }")

  {
    echo "[MAP] $name"
    echo "[INFO] $DIMENSIONS | ${FILESIZE_MB}MB"
    echo "[STEP] Skeletonize | $t1 sec | ${m1} MB"
    echo "[STEP] Autotrace   | $t2 sec | ${m2} MB"
    echo "[STEP] Linearize   | $t3 sec | ${m3} MB"
    echo "[STEP] Merge       | $t4 sec | ${m4} MB"
    echo "[PEAK_RAM] $MAP_PEAK MB"
    echo "[TOTAL] $MAP_TOTAL sec"
    echo
  } >> "$STRUCT_LOG"

  TOTAL_MAPS=$((TOTAL_MAPS + 1))

  echo "✔ Finished: merged/${name}_merged.svg"
  echo
done

TOTAL_RUN_END=$(date +%s%3N)
TOTAL_RUN_MS=$((TOTAL_RUN_END - TOTAL_RUN_START))
TOTAL_RUN_TIME=$(awk "BEGIN { printf \"%.1f\", $TOTAL_RUN_MS/1000 }")

AVG_TIME=$(awk '/\[TOTAL\]/ {sum+=$2; count++} END {if(count>0) printf "%.1f", sum/count; else print "0"}' "$STRUCT_LOG")
AVG_RAM=$(awk '/\[PEAK_RAM\]/ {sum+=$2; count++} END {if(count>0) printf "%.1f", sum/count; else print "0"}' "$STRUCT_LOG")

echo "========= RUN SUMMARY ========="
awk '/\[MAP\]/ {map=$2} /\[TOTAL\]/ {printf "%-10s | %s sec\n", map, $2}' "$STRUCT_LOG"
echo "--------------------------------"
echo "TOTAL MAPS: $TOTAL_MAPS"
echo "TOTAL TIME: $TOTAL_RUN_TIME sec"
echo "AVG TIME:   $AVG_TIME sec/map"
echo "AVG RAM:    $AVG_RAM MB/map"
echo "================================"
echo

{
  echo "========= RUN SUMMARY ========="
  awk '/\[MAP\]/ {map=$2} /\[TOTAL\]/ {printf "%-10s | %s sec\n", map, $2}' "$STRUCT_LOG"
  echo "--------------------------------"
  echo "TOTAL MAPS: $TOTAL_MAPS"
  echo "TOTAL TIME: $TOTAL_RUN_TIME sec"
  echo "AVG TIME:   $AVG_TIME sec/map"
  echo "AVG RAM:    $AVG_RAM MB/map"
  echo "================================"
} >> "$STRUCT_LOG"

echo "All files processed."