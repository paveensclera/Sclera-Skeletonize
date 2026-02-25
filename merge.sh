#!/bin/sh

# Usage: ./merge.sh input1.svg input2.svg [output.svg]

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 SVG1 SVG2 [OUT]"
    exit 1
fi

SVG1="$1"
SVG2="$2"
OUT="${3:-merged.svg}"

# 1) Copy from SVG1 until first <path>, insert rect after </metadata>
awk '
    /<\/metadata>/ {
        print
        print "<rect fill=\"white\" width=\"100%\" height=\"100%\" x=\"0\" y=\"0\"/>"
        next
    }
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