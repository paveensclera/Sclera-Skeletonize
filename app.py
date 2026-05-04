import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

app = FastAPI()

WORK_DIR = Path("/tmp/skeletonize")
WORK_DIR.mkdir(parents=True, exist_ok=Tdrue)


async def _run(cmd: list[str]) -> None:
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


@app.post("/process")
async def process(file: UploadFile = File(...)):
    job_dir = WORK_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True)

    try:
        input_png = job_dir / "input.png"
        input_png.write_bytes(await file.read())

        prefix = str(job_dir / "input")
        sk_png = job_dir / "input_sk.png"
        sk_svg = job_dir / "input_sk.svg"
        sklin_svg = job_dir / "input_sklin.svg"
        pbm = job_dir / "input.pbm"
        potrace_svg = job_dir / "input_potrace.svg"
        merged_svg = job_dir / "input_merged.svg"

        await _run(["python3", "/app/skeletonize.py", str(input_png), prefix])
        await _run(["autotrace", str(sk_png), "-centerline", "-output-file", str(sk_svg)])
        await _run(["python3", "/app/linearize.py", str(sk_svg), str(sklin_svg)])
        await _run(["magick", str(input_png), "-threshold", "99%", str(pbm)])
        await _run(["potrace", str(pbm), "-s", "-o", str(potrace_svg)])
        await _run(["bash", "/app/merge.sh", str(potrace_svg), str(sklin_svg), str(merged_svg)])

        return Response(content=merged_svg.read_bytes(), media_type="image/svg+xml")

    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
