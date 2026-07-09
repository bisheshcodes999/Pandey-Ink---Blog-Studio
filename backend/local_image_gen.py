"""Local text-to-image generation via Hugging Face `diffusers`, running
fully offline on CPU -- the no-API-key, no-billing replacement for the
old Google AI Studio image path.

Model: stabilityai/sd-turbo, a distilled Stable Diffusion checkpoint
that only needs 1-4 inference steps instead of the usual ~50. That step
count is what makes CPU generation workable at all -- a normal SD model
at 50 steps would take minutes per image on CPU; sd-turbo takes a
fraction of that. Weights get pulled from the Hugging Face Hub once on
first use (a couple GB) and are cached locally after that (usually
~/.cache/huggingface) -- every generation after the first call makes no
network requests at all.

License note: sd-turbo ships under Stability AI's non-commercial
research license. Fine for a personal/local project like this one, but
don't reuse this model in anything commercial without checking the
license first.
"""
from __future__ import annotations

import io
import sys
import threading

from backend.config import (
    LOCAL_IMAGE_GUIDANCE_SCALE,
    LOCAL_IMAGE_MODEL,
    LOCAL_IMAGE_SIZE,
    LOCAL_IMAGE_STEPS,
)
from backend.logging_utils import get_logger

logger = get_logger(__name__)

# Loaded once per process and reused for every image after that --
# reloading the weights on every call would tack another 10-20s of
# dead time onto each single image, on top of generation itself.
_pipe = None
_pipe_lock = threading.Lock()


def _get_pipeline():
    global _pipe
    if _pipe is not None:
        return _pipe

    with _pipe_lock:
        if _pipe is None:
            import torch
            from diffusers import AutoPipelineForText2Image

            logger.info(
                "Loading local image model %s (first call only, may take a "
                "minute and download weights the very first time)...",
                LOCAL_IMAGE_MODEL,
            )
            pipe = AutoPipelineForText2Image.from_pretrained(
                LOCAL_IMAGE_MODEL, torch_dtype=torch.float32
            )
            pipe.to("cpu")
            _pipe = pipe
    return _pipe


def generate_image_bytes(prompt: str) -> bytes:
    """Runs local text-to-image generation and returns PNG bytes.

    Raises RuntimeError on any failure (missing deps, out-of-memory,
    a corrupted/incomplete cached download, etc.) --
    generate_and_place_images in backend/reducer/images.py catches this
    and drops a visible "[IMAGE GENERATION FAILED]" note into the post
    instead of failing the whole run.
    """
    try:
        pipe = _get_pipeline()
    except ImportError as exc:
        raise RuntimeError(
            f"Local image generation isn't installed in this Python environment "
            f"({sys.executable}). Run: pip install -r requirements.txt using that "
            f"same environment's pip (e.g. venv\\Scripts\\python -m pip install "
            f"-r requirements.txt on Windows)."
        ) from exc

    try:
        result = pipe(
            prompt=prompt,
            num_inference_steps=LOCAL_IMAGE_STEPS,
            guidance_scale=LOCAL_IMAGE_GUIDANCE_SCALE,
            width=LOCAL_IMAGE_SIZE,
            height=LOCAL_IMAGE_SIZE,
        )
    except Exception as exc:
        raise RuntimeError(f"Local image generation failed: {exc}") from exc

    image = result.images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
