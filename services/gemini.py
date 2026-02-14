"""Gemini API integration module."""

import os
import time
from typing import Any, Optional

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
                '  GEMINI_API_KEY = "your_api_key_here"'
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

    def _is_bad_request(self, err: Exception) -> bool:
        msg = str(err).lower()
        return "bad request" in msg or "400" in msg

    def _extract_error_detail(self, err: Exception) -> str:
        details = [str(err)]

        response = getattr(err, "response", None)
        if response is not None:
            text = getattr(response, "text", None)
            if text:
                details.append(str(text))

        body = getattr(err, "body", None)
        if body:
            details.append(str(body))

        return " | detail: ".join([d for d in details if d])

    def _build_config(
        self,
        duration: Optional[int],
        aspect_ratio: Optional[str],
        resolution: Optional[str],
        minimal: bool,
    ) -> Any:
        config: dict[str, Any] = {}

        if aspect_ratio in {"16:9", "9:16", "1:1"}:
            config["aspect_ratio"] = aspect_ratio

        if not minimal:
            if duration and isinstance(duration, int) and 1 <= duration <= 8:
                config["duration_seconds"] = duration
            if resolution in {"720p", "1080p"}:
                config["resolution"] = resolution

        return types.GenerateVideosConfig(**config)

    def _poll_operation(self, operation: Any, progress_callback=None) -> Any:
        started_at = time.time()
        while not operation.done:
            if time.time() - started_at > self.GENERATION_TIMEOUT:
                raise TimeoutError("Video generation timed out")
            if progress_callback:
                elapsed = int(time.time() - started_at)
                progress_callback(0.6, f"Generating video... ({elapsed}s)")
            time.sleep(10)
            operation = self.client.operations.get(operation)
        return operation

    def _normalize_downloaded_video(self, downloaded: Any) -> bytes:
        if isinstance(downloaded, bytes):
            return downloaded
        if hasattr(downloaded, "read"):
            return downloaded.read()
        return bytes(downloaded)

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
            mime_type = self._guess_mime_type(image_bytes)
            valid, validation_msg = self.validate_image(image_bytes, mime_type)
            if not valid:
                return False, f"Image validation failed: {validation_msg}", None

            if progress_callback:
                progress_callback(0.1, "Connecting to Veo API...")

            user_prompt = (prompt or "").strip()
            if not user_prompt and mode_type == "speech":
                return False, "Please enter dialogue text.", None
            if not user_prompt and mode_type == "dance":
                user_prompt = "happy dance"

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
                progress_callback(0.3, "Submitting generation request...")

            selected_model = model if model in self.MODELS else "veo-3.1-fast-generate-preview"
            fallback_model = "veo-3.1-fast-generate-preview"
            if selected_model == fallback_model:
                fallback_model = "veo-3.1-generate-preview"

            attempts = [
                (selected_model, self._build_config(duration, aspect_ratio, resolution, minimal=False)),
                (selected_model, self._build_config(None, aspect_ratio, None, minimal=True)),
                (fallback_model, self._build_config(None, aspect_ratio, None, minimal=True)),
            ]

            operation = None
            last_error: Optional[Exception] = None
            for idx, (attempt_model, attempt_config) in enumerate(attempts):
                try:
                    operation = self.client.models.generate_videos(
                        model=attempt_model,
                        prompt=prompt_enhanced,
                        image=types.Image(image_bytes=image_bytes, mime_type=mime_type),
                        config=attempt_config,
                    )
                    break
                except Exception as err:
                    last_error = err
                    if not self._is_bad_request(err):
                        raise
                    if progress_callback and idx < len(attempts) - 1:
                        progress_callback(0.35, "Request rejected, retrying with safer options...")

            if operation is None:
                detail = self._extract_error_detail(last_error or Exception("Bad Request"))
                return False, f"Video generation request failed: {detail}", None

            if progress_callback:
                progress_callback(0.5, "Video is being generated... (usually 1-3 minutes)")

            operation = self._poll_operation(operation, progress_callback=progress_callback)

            operation_error = getattr(operation, "error", None)
            if operation_error:
                return False, f"Generation operation failed: {operation_error}", None

            response = getattr(operation, "response", None)
            if response is None or not getattr(response, "generated_videos", None):
                return False, "Generation finished but no video was returned.", None

            generated_video = response.generated_videos[0]
            downloaded = self.client.files.download(file=generated_video.video)
            video_bytes = self._normalize_downloaded_video(downloaded)

            if not video_bytes:
                return False, "Generated video file is empty.", None

            if progress_callback:
                progress_callback(1.0, "Done")

            return True, "Video generated successfully", video_bytes

        except TimeoutError:
            return False, "Video generation timed out. Please try again.", None
        except Exception as err:
            detail = self._extract_error_detail(err)
            return False, f"Error during video generation: {detail}", None


def get_gemini_service() -> GeminiService:
    return GeminiService()
