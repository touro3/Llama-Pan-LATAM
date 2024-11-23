import httpx
import os
from dotenv import load_dotenv, find_dotenv


def load_env():
    _ = load_dotenv(find_dotenv())


def get_gemini_api_key():
    load_env()
    api_key = os.getenv("ML_AI_API_KEY")
    return api_key


def transcribe_recording(recording_path):
    """
    Calls the Whisper model deployed in AI/ML API to transcribe the Speech-to-text
    """
    api_key = get_gemini_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    base_url = "https://api.aimlapi.com"

    url = f"{base_url}/stt"

    with open(recording_path, "rb") as audio_file:
        files = {
            "audio": audio_file,
        }
        data = {
            "model": "#g1_whisper-tiny",
        }
        try:
            print(url, data, files)
            response = httpx.post(url, headers=headers, data=data, files=files, timeout=40)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"HTTP Exception for {e.request.url} - {e}")

        print(response.json())
        response_data = response.json()
        transcript = response_data["results"]["channels"][0]["alternatives"][0][
            "transcript"
        ]
        return transcript