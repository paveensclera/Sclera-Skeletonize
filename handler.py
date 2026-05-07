import base64
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import runpod

WORK_DIR = Path("/tmp/skeletonize")
WORK_DIR.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def handler(job):
    image_b64 = job.get("input", {}).get("image")
    if not image_b64:
        return {"error": "missing 'image' field in input"}

    job_dir = WORK_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True)

    try:
        input_svg = job_dir / "input.svg"
        input_png = job_dir / "input.png"
        svg_text  = base64.b64decode(image_b64).decode(errors="replace")
        input_svg.write_text(svg_text)

        # Extract viewBox from input SVG to carry through to output
        vb_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_text)
        viewbox  = vb_match.group(1) if vb_match else None

        _run(["magick", str(input_svg), str(input_png)])

        prefix    = str(job_dir / "input")
        sk_png    = job_dir / "input_sk.png"
        sk_svg    = job_dir / "input_sk.svg"
        sklin_svg = job_dir / "input_sklin.svg"

        _run(["python3", "/app/skeletonize.py", str(input_png), prefix])
        _run(["autotrace", str(sk_png), "-centerline", "-output-file", str(sk_svg)])
        _run(["python3", "/app/linearize.py", str(sk_svg), str(sklin_svg)])

        output = sklin_svg.read_text()
        if viewbox:
            if 'viewBox' in output:
                output = re.sub(r'viewBox="[^"]*"', f'viewBox="{viewbox}"', output, count=1)
            else:
                output = output.replace('<svg', f'<svg viewBox="{viewbox}"', 1)

        return {"svg": base64.b64encode(output.encode()).decode()}

    except RuntimeError as exc:
        return {"error": str(exc)}
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


runpod.serverless.start({"handler": handler})
