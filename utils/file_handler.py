"""
파일 처리 유틸리티 모듈
파일 업로드, 다운로드, 저장 등을 처리합니다.
"""

import os
import tempfile
from typing import Optional, Tuple
from datetime import datetime
import streamlit as st


class FileHandler:
    """파일 업로드/다운로드 처리 클래스"""

    # 업로드 가능한 이미지 확장자
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']

    # 최대 파일 크기 (10MB)
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    def __init__(self, upload_dir: Optional[str] = None):
        """
        FileHandler 초기화

        Args:
            upload_dir: 업로드 파일 저장 디렉토리 (None이면 임시 디렉토리 사용)
        """
        if upload_dir:
            self.upload_dir = upload_dir
            os.makedirs(upload_dir, exist_ok=True)
        else:
            self.upload_dir = tempfile.gettempdir()

    def validate_uploaded_file(self, uploaded_file) -> Tuple[bool, str]:
        """
        업로드된 파일 유효성 검사

        Args:
            uploaded_file: Streamlit의 UploadedFile 객체

        Returns:
            (유효여부, 에러메시지)
        """
        # 파일 존재 확인
        if uploaded_file is None:
            return False, "파일이 업로드되지 않았습니다."

        # 파일 형식 확인
        if uploaded_file.type not in self.ALLOWED_MIME_TYPES:
            return False, (
                f"지원하지 않는 파일 형식입니다: {uploaded_file.type}\n"
                f"지원 형식: {', '.join(self.ALLOWED_MIME_TYPES)}"
            )

        # 파일 크기 확인
        file_size = uploaded_file.size
        if file_size > self.MAX_FILE_SIZE_BYTES:
            size_mb = file_size / 1024 / 1024
            return False, (
                f"파일 크기가 {self.MAX_FILE_SIZE_MB}MB를 초과했습니다.\n"
                f"현재 크기: {size_mb:.1f}MB"
            )

        # 파일명 확인
        if not self._has_valid_extension(uploaded_file.name):
            return False, (
                f"지원하지 않는 파일 확장자입니다.\n"
                f"지원 확장자: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

        return True, ""

    def _has_valid_extension(self, filename: str) -> bool:
        """파일 확장자 유효성 확인"""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in self.ALLOWED_EXTENSIONS

    def save_uploaded_file(self, uploaded_file) -> Tuple[bool, str, Optional[str]]:
        """
        업로드된 파일 저장

        Args:
            uploaded_file: Streamlit의 UploadedFile 객체

        Returns:
            (성공여부, 메시지, 저장된파일경로)
        """
        try:
            # 유효성 검사
            is_valid, error_msg = self.validate_uploaded_file(uploaded_file)
            if not is_valid:
                return False, error_msg, None

            # 고유한 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
            filename = f"dog_{timestamp}.{ext}"
            filepath = os.path.join(self.upload_dir, filename)

            # 파일 저장
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())

            return True, "파일이 저장되었습니다.", filepath

        except Exception as e:
            return False, f"파일 저장 중 오류가 발생했습니다: {str(e)}", None

    def get_file_bytes(self, filepath: str) -> Optional[bytes]:
        """
        파일을 바이트로 읽기

        Args:
            filepath: 파일 경로

        Returns:
            파일 바이트 데이터 또는 None
        """
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except Exception as e:
            st.error(f"파일 읽기 오류: {str(e)}")
            return None

    def create_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """
        임시 파일 생성

        Args:
            content: 파일 내용
            suffix: 파일 확장자

        Returns:
            생성된 임시 파일 경로
        """
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=self.upload_dir
        ) as f:
            f.write(content)
            return f.name

    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        오래된 임시 파일 정리

        Args:
            older_than_hours: 이 시간보다 오래된 파일 삭제
        """
        try:
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - (older_than_hours * 3600)

            for filename in os.listdir(self.upload_dir):
                filepath = os.path.join(self.upload_dir, filename)

                # dog_로 시작하는 파일만 처리
                if filename.startswith("dog_"):
                    file_time = os.path.getctime(filepath)
                    if file_time < cutoff_time:
                        os.remove(filepath)
        except Exception as e:
            st.warning(f"임시 파일 정리 중 오류: {str(e)}")

    def get_file_size_mb(self, filepath: str) -> float:
        """
        파일 크기(MB) 반환

        Args:
            filepath: 파일 경로

        Returns:
            파일 크기 (MB)
        """
        try:
            size_bytes = os.path.getsize(filepath)
            return size_bytes / 1024 / 1024
        except Exception:
            return 0.0


# Streamlit 세션에서 사용하는 헬퍼 함수
def init_file_handler() -> FileHandler:
    """FileHandler 인스턴스 초기화"""
    temp_dir = os.path.join(tempfile.gettempdir(), "dogaicreator")
    return FileHandler(upload_dir=temp_dir)


def display_image_preview(image_bytes: bytes, caption: str = "업로드된 이미지"):
    """
    이미지 미리보기 표시

    Args:
        image_bytes: 이미지 바이트 데이터
        caption: 캡션 텍스트
    """
    st.image(image_bytes, caption=caption, use_container_width=True)


def get_image_download_link(
    filepath: str,
    link_text: str = "다운로드",
    mime_type: str = "video/mp4"
) -> str:
    """
    다운로드 링크 HTML 생성

    Args:
        filepath: 파일 경로
        link_text: 링크 텍스트
        mime_type: MIME 타입

    Returns:
        HTML 다운로드 링크
    """
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        import base64
        b64 = base64.b64encode(data).decode()
        filename = os.path.basename(filepath)

        href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}">{link_text}</a>'
        return href
    except Exception:
        return ""