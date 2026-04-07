### Build Supporting Docker Images

Before running the pipeline, build the required images.

#### Build `autotracer` image

```bash
cd autotrace
docker build -t autotracer .
cd ..
```

#### Build `potracer` image

```bash
cd potrace
docker build -t potracer .
cd ..
```

````markdown
#### Build `potracer` image

```bash
cd potrace
docker build -t potracer .
cd ..
````

---

### Run Batch Pipeline

```bash
./pipeline.sh pngs/
```

Processes all PNG files inside `pngs/` and writes results to:

```
outputs/<filename>/
```

> Windows users → run this from **WSL**, not PowerShell or CMD.

---

### testing seperate steps

### SVG Routing Pipeline

Converts a raster PNG into a routed, merged SVG skeleton and serves a demo viewer.

1. **PNG → Skeleton PNG**

```bash
python skeletonize.py pngs/test.png outputs/test/test
```

Output → `test_sk.png`, `test_overlay.png`

2. **PNG → Base SVG**

```bash
docker run --rm -v "$(pwd):/work" potracer "magick outputs/test/test.png -threshold 99% outputs/test/test.pbm && potrace outputs/test/test.pbm -s -o outputs/test/test.svg"
```

Output → `test.svg`

3. **Skeleton PNG → Skeleton SVG**

```bash
docker run --rm -v "$(pwd)/outputs/test:/app" autotracer /app/test_sk.png -centerline -output-file /app/test_sk.svg
```

Output → `test_sk.svg`

4. **Skeleton SVG → Linearized Skeleton SVG**

```bash
python linearize.py outputs/test/test_sk.svg outputs/test/test_sklin.svg
```

Output → `test_sklin.svg`

5. **Merge SVGs**

```bash
./merge.sh outputs/test/test.svg outputs/test/test_sklin.svg outputs/test/test_merged.svg
```

Output → `test_merged.svg`

6. **Run Demo Server**

```bash
npx serve .
```

Open in Browser →
[http://localhost:3000/index.html](http://localhost:3000/index.html)

Notes:

* Must use HTTP server (not file://) or fetch() will fail.