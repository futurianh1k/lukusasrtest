# -*- coding: utf-8 -*-
"""
Sherpa-ONNX Sense-Voice RKNN Speech Recognition Web UI for RK3588
Offline Recognizer + 청크 기반 스트리밍 처리 (v5 - 모듈화 리팩토링)

🔧 v5 개선 사항:
1. 모듈화 리팩토링 (2515줄 → 여러 모듈로 분리)
2. 설정 파일 분리 (환경 변수 기반)
3. 코드 재사용성 향상
4. 유지보수성 개선

모듈 구조:
- config.py: 설정 관리
- model_loader.py: 모델 로딩
- vad_processor.py: VAD 프로세서
- matcher.py: 매칭 시스템
- emergency_alert.py: 응급 알림
- session_manager.py: 세션 관리
- report_generator.py: CSV 리포트 생성
- utils.py: 유틸리티 함수
- gradio_handlers.py: Gradio 핸들러
- gradio_ui.py: Gradio UI 생성
"""

import warnings
import logging

# 경고 메시지 무시
warnings.filterwarnings("ignore")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 분리된 모듈 import
# 패키지 외부에서 실행 가능하도록 try-except 처리
try:
    # 패키지 내부에서 실행 시 (상대 import)
    from . import config  # noqa: F401
    from .model_loader import load_model
    from .gradio_ui import create_ui
except ImportError:
    # 패키지 외부에서 직접 실행 시 (절대 import)
    import config  # noqa: F401
    from model_loader import load_model
    from gradio_ui import create_ui

# ====================
# 메인 실행
# ====================
if __name__ == "__main__":
    logger.info("\n" + "=" * 60)
    logger.info("🚀 Sherpa-ONNX Sense-Voice 음성인식 UI 시작")
    logger.info("🖥️ RK3588 NPU 최적화 (v5 - 모듈화 리팩토링)")
    logger.info("=" * 60 + "\n")

    try:
        load_model()
    except Exception as e:
        logger.error(f"\n❌ 모델 로딩 실패: {e}", exc_info=True)
        logger.error("\n프로그램 종료")
        exit(1)

    demo = create_ui()
    demo.queue()

    logger.info("\n" + "=" * 60)
    logger.info("🌐 웹 서버 시작...")
    logger.info("💡 RK3588 NPU 4코어 사용:")
    logger.info("   taskset 0x0F python demo_vad_final.py")
    logger.info("=" * 60)

    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            inbrowser=False,
            ssl_keyfile="server.key",
            ssl_certfile="server.crt",
        )
    except Exception as e:
        # SSL 검증 오류는 무시하고 서버는 계속 실행됨
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
            logger.warning(f"⚠️ SSL 검증 경고 (무시됨): {e}")
            logger.info(
                "✅ 서버는 정상적으로 실행 중입니다. 브라우저에서 접속해주세요."
            )
            # 서버가 이미 시작되었으므로 무한 대기
            import time

            while True:
                time.sleep(1)
        else:
            raise
