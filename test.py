"""Test script for Cloud Run deployment."""
import requests
import sys
import time


def test_health(base_url: str):
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{base_url}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_transcription(base_url: str, audio_file: str):
    """Test transcription endpoint."""
    print(f"\nTesting transcription with {audio_file}...")

    with open(audio_file, "rb") as f:
        files = {"file": (audio_file, f, "audio/mpeg")}
        start_time = time.time()
        response = requests.post(f"{base_url}/transcribe", files=files)
        end_time = time.time()

    print(f"Status: {response.status_code}")
    print(f"Execution time: {end_time - start_time:.2f}s")

    if response.status_code == 200:
        result = response.json()
        print(f"Notes detected: {result['count']}")
        print(f"Model: {result['model']}")
        print(f"Polyphonic: {result['polyphonic']}")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200


def main():
    if len(sys.argv) < 2:
        print("Usage: python test.py <base_url> [audio_file]")
        print("Example: python test.py https://guitar-transcription-xxx.a.run.app test.mp3")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    audio_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Test health
    if not test_health(base_url):
        print("Health check failed!")
        sys.exit(1)

    # Test transcription if audio file provided
    if audio_file:
        if not test_transcription(base_url, audio_file):
            print("Transcription test failed!")
            sys.exit(1)

    print("\nAll tests passed!")


if __name__ == "__main__":
    main()
