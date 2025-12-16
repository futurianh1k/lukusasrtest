# -*- coding: utf-8 -*-
"""
모델 로딩 모듈

Sherpa-ONNX 모델 로딩 및 초기화
"""

import os
import logging

# 패키지 외부에서 실행 가능하도록 try-except 처리
try:
    from .config import MODEL_DIR, MODEL_PATH, TOKENS_PATH
    from .vad_processor import VADStreamingProcessor
    from .exceptions import ModelLoadError
except ImportError:
    from config import MODEL_DIR, MODEL_PATH, TOKENS_PATH
    from vad_processor import VADStreamingProcessor
    from exceptions import ModelLoadError

logger = logging.getLogger(__name__)

# sherpa-onnx import
try:
    import sherpa_onnx
except ImportError:
    raise ImportError(
        "sherpa-onnx를 찾을 수 없습니다.\n"
        "다음 명령어로 설치해주세요:\n"
        "pip install sherpa-onnx -f https://k2-fsa.github.io/sherpa/onnx/rk-npu.html"
    )

# 전역 recognizer 변수
recognizer = None
vad_stream_processor = None


def load_model():
    """Offline Recognizer 로드"""
    global recognizer, vad_stream_processor

    logger.info("=" * 60)
    logger.info("🔄 Sherpa-ONNX Sense-Voice RKNN 모델 로딩 중...")
    logger.info("📦 모델: sense-voice (zh, en, ja, ko, yue)")
    logger.info("🖥️ 플랫폼: RK3588 - NPU 최적화")
    logger.info("=" * 60)

    if not os.path.exists(MODEL_DIR):
        raise ModelLoadError(f"모델 디렉토리 없음: {MODEL_DIR}")

    required_files = {
        "RKNN Model": MODEL_PATH,
        "Tokens": TOKENS_PATH,
    }

    logger.info("📁 모델 파일 확인:")
    for name, path in required_files.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024**2)
            logger.info(f"  ✅ {name}: {os.path.basename(path)} ({size:.2f} MB)")
        else:
            raise ModelLoadError(f"필수 파일 없음: {name}")

    logger.info("⚙️ Offline Recognizer 초기화 중...")
    try:
        recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=MODEL_PATH,
            tokens=TOKENS_PATH,
            num_threads=4,
            provider="rknn",
            use_itn=True,
            debug=False,
        )
        logger.info("✅ Offline Recognizer 로딩 완료!")

        # VAD 기반 스트림 프로세서 생성
        vad_stream_processor = VADStreamingProcessor(
            recognizer, 
            sample_rate=16000,
            vad_enabled=True  # VAD 활성화
        )
        logger.info("✅ VADStreamingProcessor 생성 완료 (VAD 지원)")

    except ModelLoadError:
        raise
    except Exception as e:
        logger.error(f"❌ Recognizer 로딩 실패: {e}", exc_info=True)
        raise ModelLoadError(f"모델 로딩 실패: {str(e)}") from e

    logger.info("=" * 60)
    logger.info("✅ 모델 로딩 완료!")
    logger.info("=" * 60)

