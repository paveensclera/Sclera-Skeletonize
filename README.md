# SVG Routing Pipeline

Converts PNG → routed merged SVG using skeletonization, autotrace, and potrace.

---
## Setup

```bash
docker build -t autopaths_pipeline .
```

---
## Run

**macOS / Linux**

```bash
docker run --rm -v $(pwd)/pngs:/data -v $(pwd)/outputs:/output autopaths_pipeline /data
```

**Windows (PowerShell)**

```powershell
docker run --rm -v ${PWD}/pngs:/data -v ${PWD}/outputs:/output autopaths_pipeline /data
```

---
## Output

```
outputs/
  merged/          ← final SVGs
  <name>/          ← intermediates
  autopaths_*.log  ← timing + RAM log
```

## Testing Steps Individually

**1. Skeletonize**
```bash
python3 skeletonize.py pngs/test.png outputs/test/test
```

**2. Autotrace**
```bash
autotrace outputs/test/test_sk.png -centerline -output-file outputs/test/test_sk.svg
```

**3. Linearize**
```bash
python3 linearize.py outputs/test/test_sk.svg outputs/test/test_sklin.svg
```

**4. Potrace**
```bash
magick outputs/test/test.png -threshold 99% outputs/test/test.pbm
potrace outputs/test/test.pbm -s -o outputs/test/test.svg
```

**5. Merge**
```bash
./merge.sh outputs/test/test.svg outputs/test/test_sklin.svg outputs/test/test_merged.svg
```

---