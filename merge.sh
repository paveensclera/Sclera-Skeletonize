#!/bin/sh

SVG1=test.svg 
SVG2=test_sklin.svg 
OUT=merged.svg 

# 1) Copy from SVG1 until first <path>
awk '
    /<path/ { exit }
    { print }
' "$SVG1" > "$OUT"

# 2) Add all paths from SVG1
xmllint --xpath "//*[local-name()='path']" "$SVG1" >> "$OUT"

# 3) Close the first <g>
echo "</g>" >> "$OUT"

# 4) Append ALL <path> elements from SVG2 (no g tag expected)
xmllint --xpath "//*[local-name()='path']" "$SVG2" >> "$OUT"

# 5) Close the SVG
echo "</svg>" >> "$OUT"