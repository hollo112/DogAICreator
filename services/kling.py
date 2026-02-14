"""
Kling AI API integration module.
"""

import os
import time
import base64
from typing import Optional

import jwt
import requests
import streamlit as st


class KlingService:
    """Video generation service backed by Kling AI."""

    BASE_URL = "https://api.klingai.com/v1"

    MODELS = {
        "kling-v2-6": "Kling v2.6",
        "kling-video-o1": "Kling Video O1",
    }

    ALLOWED_DURATIONS = [5, 10]

    def __init__(self, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.access_key = access_key or st.secrets.get("KLING_ACCESS_KEY") or os.getenv("KLING_ACCESS_KEY")
        self.secret_key = secret_key or st.secrets.get("KLING_SECRET_KEY") or os.getenv("KLING_SECRET_KEY")
        if not self.access_key or not self.secret_key:
            raise ValueError("KLING_ACCESS_KEY and KLING_SECRET_KEY must be configured")

    def _generate_jwt_token(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.access_key,
            "exp": now + 1800,
            "nbf": now - 5,
            "iat": now,
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._generate_jwt_token()}",
            "Content-Type": "application/json",
        }

    def generate_video(
        self,
        image_bytes: bytes,
        prompt: str,
        progress_callback=None,
        model: str = "kling-v2-6",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        mode_type: str = "speech",
    ) -> tuple[bool, str, Optional[bytes]]:
        """Generate image-to-video with Kling AI."""
        try:
            if progress_callback:
                progress_callback(0.05, "Kling AI 연결 중...")

            user_prompt = prompt.strip()
            if not user_prompt:
                return False, "프롬프트가 비어 있습니다.", None

            # Keep user prompt as highest priority for better adherence.
            if mode_type == "dance":
                prompt_enhanced = (
                    "Follow USER_PROMPT as the highest-priority instruction.\n"
                    "Preserve the dog's identity and the original background.\n"
                    "Make the dog move naturally and energetically according to USER_PROMPT.\n"
                    "No subtitles, no extra text overlays.\n\n"
                    f"USER_PROMPT:\n{user_prompt}"
                )
            else:
                prompt_enhanced = (
                    "The dog in the photo opens its mouth and speaks the following dialogue "
                    "with accurate lip-sync mouth movements.\n"
                    "Voice: a cute 3-year-old Korean girl, cheerful and adorable tone.\n"
                    "The dog's mouth moves naturally matching each syllable of the dialogue.\n"
                    "Preserve the dog's identity and the original background.\n"
                    "No subtitles, no extra text overlays.\n\n"
                    f"Dialogue:\n{user_prompt}"
                )

            if progress_callback:
                progress_callback(0.10, "영상 생성 요청 중...")

            if duration not in self.ALLOWED_DURATIONS:
                duration = self.ALLOWED_DURATIONS[0]

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            request_body = {
                "model_name": model,
                "image": image_b64,
                "prompt": prompt_enhanced,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
                "mode": "pro",
                "enable_audio": True,
            }

            response = requests.post(
                f"{self.BASE_URL}/videos/image2video",
                headers=self._get_headers(),
                json=request_body,
                timeout=30,
            )

            if response.status_code != 200:
                return False, f"API request failed ({response.status_code}): {response.text}", None

            resp_data = response.json()
            if resp_data.get("code") != 0:
                return False, f"API error: {resp_data.get('message', 'unknown error')}", None

            task_id = resp_data.get("data", {}).get("task_id")
            if not task_id:
                return False, "Task ID missing", None

            if progress_callback:
                progress_callback(0.15, "AI가 영상을 생성하고 있습니다... (보통 2-5분)")

            poll_count = 0
            max_polls = 60
            max_progress = 0.75
            poll_data = None

            while poll_count < max_polls:
                time.sleep(10)
                poll_count += 1

                poll_response = requests.get(
                    f"{self.BASE_URL}/videos/image2video/{task_id}",
                    headers=self._get_headers(),
                    timeout=30,
                )
                if poll_response.status_code != 200:
                    continue

                poll_data = poll_response.json()
                task_status = poll_data.get("data", {}).get("task_status", "")

                if progress_callback:
                    elapsed = poll_count * 10
                    progress = min(0.15 + (poll_count * 0.03), max_progress)
                    progress_callback(progress, f"생성 중... ({elapsed}초 경과)")

                if task_status == "succeed":
                    break
                if task_status == "failed":
                    fail_msg = poll_data.get("data", {}).get("task_status_msg", "unknown error")
                    return False, f"영상 생성 실패: {fail_msg}", None
            else:
                return False, "영상 생성 시간 초과 (10분)", None

            if progress_callback:
                progress_callback(0.80, "영상 생성 완료! 파일 다운로드 중...")

            videos = poll_data.get("data", {}).get("task_result", {}).get("videos", []) if poll_data else []
            if not videos:
                return False, "생성된 영상을 찾을 수 없습니다", None

            video_url = videos[0].get("url")
            if not video_url:
                return False, "영상 URL을 찾을 수 없습니다", None

            for i in range(3):
                if progress_callback:
                    progress_callback(0.85 + (i * 0.05), f"영상 파일 다운로드 중... ({i + 1}/3)")
                dl_response = requests.get(video_url, timeout=120)
                if dl_response.status_code == 200 and len(dl_response.content) > 10240:
                    if progress_callback:
                        progress_callback(1.0, "완료!")
                    return True, "성공", dl_response.content
                time.sleep(3)

            return False, f"비디오 다운로드 실패 ({dl_response.status_code})", None

        except Exception as e:
            return False, f"오류 발생: {str(e)}", None


def get_kling_service() -> KlingService:
    return KlingService()
