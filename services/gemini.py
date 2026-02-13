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
    ) -> tuple[bool, str, Optional[bytes]]:
        """Generate an image-to-video clip with Veo.

        The `duration` parameter is accepted for interface compatibility but
        Veo duration is fixed to 4 seconds in this app.
        """
        try:
            if progress_callback:
                progress_callback(0.1, "Veo API 연결 중...")

            prompt_enhanced = (
                "사진 속 강아지가 프롬프트에 맞춰 자연스럽게 움직이는 영상을 생성해주세요. "
                "강아지의 외형과 배경은 유지하고, 행동만 자연스럽게 변화시켜주세요.\n\n"
                f"프롬프트: {prompt}"
            )

            if progress_callback:
                progress_callback(0.3, "비디오 생성 요청 중...")

            operation = self.client.models.generate_videos(
                model=model,
                prompt=prompt_enhanced,
                image=types.Image(
                    image_bytes=image_bytes,
                    mime_type=self._guess_mime_type(image_bytes),
                ),
                config=types.GenerateVideosConfig(
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                    duration_seconds=4,
                ),
            )

            if progress_callback:
                progress_callback(0.5, "비디오 생성 대기 중... (약 1-3분 소요)")

            started_at = time.time()
            while not operation.done:
                if time.time() - started_at > self.GENERATION_TIMEOUT:
                    return False, "비디오 생성 시간 초과", None
                if progress_callback:
                    progress_callback(0.6, "생성 중...")
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
            return False, f"비디오 생성 중 오류: {str(e)}", None


def get_gemini_service() -> GeminiService:
    return GeminiService()
