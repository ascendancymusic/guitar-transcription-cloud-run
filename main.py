"""
Google Cloud Run Guitar Transcription

Model: guitar-gaps.pth (GAPS, ISMIR 2024)
Architecture: CRNN (same as piano transcription)
Polyphonic: Yes - handles chords and multiple voices
State-of-the-art: 91.2% F1 on GuitarSet

Optimizations:
- CPU-only for faster cold starts (no GPU overhead)
- Thread tuning for CPU inference
- Optimized for Cloud Run (no lazy page loading issues)
- Consistent 3-7s execution time

Deploy: gcloud run deploy guitar-transcription --source . --memory 8Gi --cpu 2 --min-instances 0
"""

import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("KMP_BLOCKTIME", "1")
os.environ.setdefault("KMP_AFFINITY", "granularity=fine,compact,1,0")

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse


# =========================
# APP CONFIG
# =========================

@asynccontextmanager
async def lifespan(app):
    import threading
    print("Startup: loading model synchronously...")
    load_model()
    print("Startup: model loaded, server ready.")
    yield

app = FastAPI(title="Guitar Transcription API", lifespan=lifespan)

MODEL_DIR = "/models"
MODEL_FILE_PATH = f"{MODEL_DIR}/guitar-gaps.pth"

# Global model instance (loaded once per container)
model = None
model_loading = False


# =========================
# MODEL LOADING
# =========================

def load_model():
    """Load model once when container starts."""
    global model, model_loading
    model_loading = True
    print("load_model: importing dependencies...")
    try:
        import torch
        from hf_midi_transcription import MidiTranscriptionModel

        torch.set_num_threads(2)

        if not Path(MODEL_FILE_PATH).exists():
            raise RuntimeError(f"Model missing: {MODEL_FILE_PATH}")

        print("load_model: loading guitar model...")
        model = MidiTranscriptionModel(
            instrument="guitar",
            checkpoint_path=MODEL_FILE_PATH,
            device="cpu",
            batch_size=8,
        )
        model_loading = False
        print("Guitar model ready on CPU.")
    except Exception as e:
        model_loading = False
        print(f"Failed to load model: {e}")
        raise


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
async def health():
    """Health check endpoint."""
    if model_loading:
        return JSONResponse(status_code=503, content={
            "status": "loading",
            "model": "guitar-gaps.pth",
            "device": "cpu",
        })
    return {
        "status": "healthy",
        "model": "guitar-gaps.pth",
        "device": "cpu",
    }


# =========================
# TRANSCRIPTION ENDPOINT
# =========================

@app.post("/transcribe")
async def transcribe(request: Request, file: UploadFile = File(...)):
    """
    Upload audio file (mp3/wav/ogg/etc)
    Returns guitar note events (polyphonic).
    """
    if model_loading:
        raise HTTPException(status_code=503, detail="Model still loading, try again shortly")
    # -------------------------
    # AUTH (optional)
    # -------------------------
    expected = os.environ.get("CLOUD_RUN_API")
    if expected:
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
        if token != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    # -------------------------
    # READ FILE
    # -------------------------
    content = await file.read()

    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    suffix = (Path(file.filename or "audio").suffix or ".wav").lower()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        input_path = f.name

    midi_path = input_path + ".mid"

    try:
        # -------------------------
        # AUDIO CONVERSION
        # -------------------------
        import subprocess
        import librosa

        wav_path = input_path + ".wav"

        subprocess.run(
            [
                "ffmpeg",
                "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                "-y", wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        # Load audio
        audio, _ = librosa.load(wav_path, sr=16000, mono=True)

        # Clean up wav immediately
        try:
            os.unlink(wav_path)
        except Exception:
            pass

        # -------------------------
        # TRANSCRIPTION
        # -------------------------
        import torch

        with torch.inference_mode():
            model.transcribe_audio_array(audio, midi_path)

        # -------------------------
        # MIDI PARSING
        # -------------------------
        import pretty_midi

        pm = pretty_midi.PrettyMIDI(midi_path)

        notes = []
        for instrument in pm.instruments:
            for note in instrument.notes:
                notes.append(
                    {
                        "midi": note.pitch,
                        "startTime": round(float(note.start), 4),
                        "duration": round(float(note.end - note.start), 4),
                        "velocity": note.velocity,
                    }
                )

        notes.sort(key=lambda x: x["startTime"])

        return {
            "notes": notes,
            "count": len(notes),
            "model": "guitar-gaps",
            "polyphonic": True,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(midi_path):
                os.unlink(midi_path)
        except Exception:
            pass
