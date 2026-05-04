import base64
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
        input_png = job_dir / "input.png"
        input_png.write_bytes(base64.b64decode(image_b64))

        prefix    = str(job_dir / "input")
        sk_png    = job_dir / "input_sk.png"
        sk_svg    = job_dir / "input_sk.svg"
        sklin_svg = job_dir / "input_sklin.svg"

        _run(["python3", "/app/skeletonize.py", str(input_png), prefix])
        _run(["autotrace", str(sk_png), "-centerline", "-output-file", str(sk_svg)])
        _run(["python3", "/app/linearize.py", str(sk_svg), str(sklin_svg)])

        return {"svg": base64.b64encode(sklin_svg.read_bytes()).decode()}

    except RuntimeError as exc:
        return {"error": str(exc)}
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


runpod.serverless.start({"handler": handler})
