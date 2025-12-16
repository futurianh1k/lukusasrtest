# -*- coding: utf-8 -*-
"""
ASR 서버 설정 모듈

환경 변수 기반 설정 관리
"""

import os
import logging

logger = logging.getLogger(__name__)

# ====================
# 모델 설정
# ====================
MODEL_DIR = os.path.join(
    os.getcwd(),
    "models",
    os.getenv(
        "ASR_MODEL_DIR",
        "sherpa-onnx-rk3588-30-seconds-sense-voice-zh-en-ja-ko-yue-2024-07-17",
    ),
)

MODEL_PATH = os.path.join(MODEL_DIR, "model.rknn")
TOKENS_PATH = os.path.join(MODEL_DIR, "tokens.txt")

# ====================
# 언어 매핑
# ====================
LANGUAGE_MAP = {
    "자동 감지": "auto",
    "한국어": "ko",
    "중국어": "zh",
    "영어": "en",
    "일본어": "ja",
    "광동어": "yue",
}

# ====================
# 정답 데이터 (Ground Truth)
# ====================
GROUND_TRUTHS = [
    # 일상 상황 10개
    "회의는 오후 세 시에 시작해 알림 설정해 줘",
    "내일 아침 일곱 시에 기상 알람을 추가해",
    "거실 불 끄고 공기청정기 약하게 켜",
    "오늘 점심은 김치볶음밥 두 개 주문할까",
    "블루투스 이어폰 배터리 잔량 얼마야",
    "일정에 고객 미팅 오후 두 시로 등록해",
    "와이파이가 자꾸 끊겨 속도 테스트 해봐",
    "영수증 사진을 스캔해서 이메일로 보내",
    "주말에 가족 영화 추천해 줘 액션 말고",
    "날씨 어때 우산 챙겨야 할까",
    # 응급 상황 10개
    "도와줘 사람이 쓰러졌어",
    "119에 바로 신고해 호흡이 멈춘 것 같아",
    "불이야 주방에서 연기가 나",
    "심장이 아파 가슴이 조여 와",
    "큰 사고야 피가 많이 나 위치 전송해 줘",
    "알러지 반응이야 숨쉬기 힘들어.",
    "어지럽고 구토가 나 구급차 호출해",
    "노약자가 계단에서 넘어졌어 의식이 희미해",
    "가스 냄새가 심해 즉시 환기하고 신고해",
    "아이 체온이 40도야 응급실 안내해 줘",
]

LABELS = ["일상"] * 10 + ["응급"] * 10

# ====================
# 응급 상황 API 설정
# ====================
EMERGENCY_API_CONFIG = {
    "enabled": os.getenv("EMERGENCY_API_ENABLED", "true").lower() == "true",
    "api_endpoints": [
        {
            "name": "Emergency Alert API (JSON)",
            "url": os.getenv(
                "EMERGENCY_API_URL_JSON",
                "http://localhost:8080/api/emergency/quick",  # 환경변수로 오버라이드
            ),
            "enabled": True,
            "method": "POST",
            "type": "json",
        },
        {
            "name": "Emergency Alert API (Multipart)",
            "url": os.getenv(
                "EMERGENCY_API_URL_MULTIPART",
                "http://localhost:8080/api/emergency/quick/{watchId}",  # 환경변수로 오버라이드
            ),
            "enabled": os.getenv("EMERGENCY_API_MULTIPART_ENABLED", "false").lower()
            == "true",
            "method": "POST",
            "type": "multipart",
        },
    ],
    "watch_id": os.getenv("EMERGENCY_WATCH_ID", ""),  # 환경변수 필수
    "sender_id": os.getenv("EMERGENCY_SENDER_ID", "voice_asr_system"),
    "include_image_url": os.getenv("EMERGENCY_INCLUDE_IMAGE_URL", "true").lower()
    == "true",
    "image_base_url": os.getenv(
        "EMERGENCY_IMAGE_BASE_URL",
        "http://localhost:8080/api/images",  # 환경변수로 오버라이드
    ),
    "fcm_project_id": os.getenv(
        "EMERGENCY_FCM_PROJECT_ID", "emergency-alert-system-f27e6"
    ),
}

# ====================
# SSL 설정
# ====================
# 프로덕션 환경에서는 SSL 검증을 활성화해야 함
SSL_VERIFY = os.getenv("SSL_VERIFY", "false").lower() == "true"

if not SSL_VERIFY:
    logger.warning(
        "⚠️ SSL 검증이 비활성화되어 있습니다. 프로덕션 환경에서는 활성화하세요."
    )
    # 자체 서명 인증서 사용 시 Gradio 내부 API 호출 SSL 검증 비활성화
    os.environ["GRADIO_SSL_VERIFY"] = "false"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["PYTHONHTTPSVERIFY"] = "0"

    # httpx SSL 검증 비활성화 (자체 서명 인증서 사용 시)
    import ssl

    ssl._create_default_https_context = ssl._create_unverified_context

    # httpx 클라이언트의 SSL 검증 비활성화를 위한 패치
    try:
        import httpx

        # httpx의 기본 SSL 검증 비활성화
        original_init = httpx.Client.__init__

        def patched_init(self, *args, verify=False, **kwargs):
            return original_init(self, *args, verify=False, **kwargs)

        httpx.Client.__init__ = patched_init

        original_async_init = httpx.AsyncClient.__init__

        def patched_async_init(self, *args, verify=False, **kwargs):
            return original_async_init(self, *args, verify=False, **kwargs)

        httpx.AsyncClient.__init__ = patched_async_init
    except ImportError:
        pass
