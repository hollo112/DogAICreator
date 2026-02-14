"""
Gemini API integration module.
"""

import os
import time
from typing import Optional

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except Exception:
    genai = None
    types = None
    HAS_GOOGLE_GENAI = False

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class GeminiService:
    """Video generation service backed by Gemini/Veo."""

    MODELS = {
        "veo-3.1-generate-preview": "Veo 3.1 Standard",
        "veo-3.1-fast-generate-preview": "Veo 3.1 Fast",
    }

    SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
    MAX_FILE_SIZE = 10 * 1024 * 1024
    GENERATION_TIMEOUT = 300

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_GOOGLE_GENAI:
            raise ValueError(
                "google-genai package is not installed.\n\n"
                "Install with:\n"
                "  .venv\\Scripts\\python.exe -m pip install -r requirements.txt"
            )

        self.api_key = api_key
        if not self.api_key and HAS_STREAMLIT:
            self.api_key = st.secrets.get("GEMINI_API_KEY")
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured.\n\n"
                "Add to .streamlit/secrets.toml:\n"
                "  GEMINI_API_KEY = \"your_api_key_here\""
            )

        self.client = genai.Client(api_key=self.api_key)

    def validate_image(self, image_data: bytes, image_type: str) -> tuple[bool, str]:
        if len(image_data) > self.MAX_FILE_SIZE:
            return False, f"File size exceeds 10MB ({len(image_data) / 1024 / 1024:.1f}MB)"
        if image_type not in self.SUPPORTED_IMAGE_TYPES:
            return False, f"Unsupported file type: {image_type}"
        if len(image_data) < 100:
            return False, "Invalid image file"
        return True, ""

    def _guess_mime_type(self, image_bytes: bytes) -> str:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
            return "image/webp"
        return "image/jpeg"

    def generate_video(
        self,
        image_bytes: bytes,
        prompt: str,
        progress_callback=None,
        model: str = "veo-3.1-fast-generate-preview",
        duration: int = 4,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        mode_type: str = "speech",
    ) -> tuple[bool, str, Optional[bytes]]:
        """Generate an image-to-video clip with Veo."""
        try:
            if progress_callback:
                progress_callback(0.1, "Veo API 연결 중...")

            user_prompt = prompt.strip()

            if mode_type == "dance":
                prompt_enhanced = (
                    "The dog in the photo stands up on two legs and dances energetically.\n"
                    "Preserve the dog's exact appearance and the original background.\n"
                    "The dog moves naturally and rhythmically to the music.\n"
                    "No subtitles, no text overlays.\n\n"
                    f"Dance style: {user_prompt}"
                )
            else:
                prompt_enhanced = (
                    "The dog in the photo opens its mouth and speaks the following dialogue "
                    "with accurate lip-sync mouth movements.\n"
                    "Voice: a cute 3-year-old Korean girl, cheerful and adorable tone.\n"
                    "The dog's mouth moves naturally matching each syllable of the dialogue.\n"
                    "Preserve the dog's exact appearance and the original background.\n"
                    "No subtitles, no text overlays.\n\n"
                    f"Dialogue: {user_prompt}"
                )

            if progress_callback:
                progress_callback(0.3, "비디오 생성 요청 중...")

            # GenerateVideosConfig는 camelCase 파라미터 사용
            config_kwargs = {
                "aspectRatio": aspect_ratio,
                "generateAudio": True,
            }
            if duration and duration in (4, 6, 8):
                config_kwargs["durationSeconds"] = duration

            operation = self.client.models.generate_videos(
                model=model,
                prompt=prompt_enhanced,
                image=types.Image(
                    imageBytes=image_bytes,
                    mimeType=self._guess_mime_type(image_bytes),
                ),
                config=types.GenerateVideosConfig(**config_kwargs),
            )

            if progress_callback:
                progress_callback(0.5, "비디오 생성 대기 중... (약 1-3분 소요)")

            started_at = time.time()
            while not operation.done:
                if time.time() - started_at > self.GENERATION_TIMEOUT:
                    return False, "비디오 생성 시간 초과", None
                if progress_callback:
                    elapsed = int(time.time() - started_at)
                    progress_callback(0.6, f"생성 중... ({elapsed}초 경과)")
                time.sleep(10)
                operation = self.client.operations.get(operation)

            if progress_callback:
                progress_callback(0.9, "결과 처리 중...")

            generated_video = operation.response.generated_videos[0]
            video_bytes = self.client.files.download(file=generated_video.video)

            if progress_callback:
                progress_callback(1.0, "완료!")

            return True, "비디오 생성 완료", video_bytes

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response'):
                try:
                    error_msg = f"{error_msg} | 상세: {e.response.text}"
                except Exception:
                    pass
            return False, f"비디오 생성 중 오류: {error_msg}", None


def get_gemini_service() -> GeminiService:
    return GeminiService()