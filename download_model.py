"""Download model at build time."""
import os
from pathlib import Path
from huggingface_hub import hf_hub_download

MODEL_DIR = "/models"
MODEL_FILE_PATH = f"{MODEL_DIR}/guitar-gaps.pth"


def download_model():
    """Download guitar transcription model from HuggingFace."""
    Path(MODEL_DIR).mkdir(parents=True, exist_ok=True)

    print("Downloading guitar-gaps.pth from HuggingFace...")

    hf_hub_download(
        repo_id="xavriley/midi-transcription-models",
        filename="guitar-gaps.pth",
        local_dir=MODEL_DIR,
    )

    size_mb = Path(MODEL_FILE_PATH).stat().st_size / (1024 * 1024)
    print(f"Model size: {size_mb:.1f} MB")

    if size_mb < 50:
        raise RuntimeError("Model download failed or corrupted")


if __name__ == "__main__":
    download_model()
