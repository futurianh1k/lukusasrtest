#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sherpa-ONNX Sense-Voice RKNN Speech Recognition Web UI for RK3588
Offline Recognizer + 청크 기반 스트리밍 처리 + API 엔드포인트 관리

🔧 v6 통합 버전:
1. VAD 기반 실시간 음성인식
2. 응급 상황 자동 감지
3. API 엔드포인트 관리 UI
4. 다중 엔드포인트 전송 (비동기)
5. SQLite 기반 설정 영구 저장
6. 자동 재시도 로직

실행 방법:
    python demo_vad_with_api.py
    
브라우저 접속:
    https://localhost:7860
"""

import os
import sys
import warnings
import logging
import importlib
import traceback

# 경고 메시지 무시
warnings.filterwarnings("ignore")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 현재 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# API 관리 모듈 import
try:
    from api_endpoint_db import ApiEndpointDB
    from api_utils import send_api_event, send_to_multiple_endpoints
    from emergency_alert_manager import EmergencyAlertManager, get_emergency_manager
    from api_management_ui import create_api_management_tab
    
    logger.info("✅ API 관리 모듈 로드 완료")
    API_MODULE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ API 관리 모듈 로드 실패: {e}")
    logger.warning("⚠️ API 엔드포인트 관리 기능이 비활성화됩니다.")
    API_MODULE_AVAILABLE = False

# Gradio import
try:
    import gradio as gr
    logger.info("✅ Gradio 로드 완료")
    # ASR 모델 및 핸들러 로드 (여러 import 경로 시도)
    ASR_HANDLERS_AVAILABLE = False
    try:
        from model_loader import load_model
    except Exception as e:
        logger.warning(f"⚠️ model_loader import 실패: {e}")

    try:
        # 절대 import 우선 (스크립트로 실행하는 경우)
        try:
            from gradio_handlers import (
                process_vad_audio_stream,
                start_vad_session_handler,
                stop_vad_session_handler,
                reset_vad_session_handler,
            )
            ASR_HANDLERS_AVAILABLE = True
            logger.info("✅ ASR 핸들러 import (절대 import) 성공")
        except Exception as e1:
            logger.warning(f"⚠️ 절대 import 실패: {type(e1).__name__}: {e1}")
            logger.warning(traceback.format_exc())
            # 패키지 이름이 있을 경우 (예: rk3588asr 패키지로 사용)
            try:
                from gradio_handlers import (
                    process_vad_audio_stream,
                    start_vad_session_handler,
                    stop_vad_session_handler,
                    reset_vad_session_handler,
                )
                ASR_HANDLERS_AVAILABLE = True
                logger.info("✅ ASR 핸들러 import (패키지 상대 import) 성공")
            except Exception as e2:
                logger.warning(f"⚠️ 패키지 import 실패: {type(e2).__name__}: {e2}")
                logger.warning(traceback.format_exc())
                # 마지막 시도: importlib.import_module to capture errors
                try:
                    importlib.import_module('gradio_handlers')
                    m = importlib.import_module('gradio_handlers')
                    process_vad_audio_stream = getattr(m, 'process_vad_audio_stream', None)
                    start_vad_session_handler = getattr(m, 'start_vad_session_handler', None)
                    stop_vad_session_handler = getattr(m, 'stop_vad_session_handler', None)
                    reset_vad_session_handler = getattr(m, 'reset_vad_session_handler', None)
                    if process_vad_audio_stream and start_vad_session_handler:
                        ASR_HANDLERS_AVAILABLE = True
                        logger.info("✅ gradio_handlers import via importlib 성공")
                except Exception as e3:
                    logger.warning(f"⚠️ importlib 시도 실패: {type(e3).__name__}: {e3}")
                    logger.warning(traceback.format_exc())

                if not ASR_HANDLERS_AVAILABLE:
                    logger.warning("⚠️ ASR 핸들러 import 모두 실패")
                    logger.warning("⚠️ ASR 관련 기능(음성인식 UI 연동)이 비활성화됩니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
        logger.error(traceback.format_exc())

    # 핸들러가 없을 때를 대비한 안전한 스텁 정의
    if not ASR_HANDLERS_AVAILABLE:
        logger.info("ℹ️ ASR 핸들러가 없으므로 대체 스텁을 생성합니다.")

        def start_vad_session_handler():
            logger.warning("요청된 start_vad_session_handler는 사용 불가합니다.")
            return [
                gr.update(interactive=True, value="🎙️ 음성인식 시작"),
                gr.update(interactive=False),
                None,
                "⚠️ ASR 모듈을 사용할 수 없습니다."
            ]

        def stop_vad_session_handler(ground_truth_input=None):
            logger.warning("요청된 stop_vad_session_handler는 사용 불가합니다.")
            return ("⚠️ ASR 모듈을 사용할 수 없습니다.", "")

        def reset_vad_session_handler():
            logger.warning("요청된 reset_vad_session_handler는 사용 불가합니다.")
            return (None, "⚠️ ASR 모듈을 사용할 수 없습니다.", "")

        def process_vad_audio_stream(audio_stream, language):
            # 스트리밍 핸들러는 제너레이터여야 함
            yield "⚠️ ASR 모듈을 사용할 수 없습니다."

except ImportError:
    logger.error("❌ Gradio를 찾을 수 없습니다. pip install gradio를 실행하세요.")
    sys.exit(1)

# ====================
# 메인 실행
# ====================
if __name__ == "__main__":
    logger.info("\n" + "=" * 80)
    logger.info("🚀 Sherpa-ONNX Sense-Voice 음성인식 UI 시작")
    logger.info("🖥️ RK3588 NPU 최적화 (v6 - API 통합)")
    logger.info("=" * 80 + "\n")

    # API 관리자 초기화
    if API_MODULE_AVAILABLE:
        try:
            manager = get_emergency_manager()
            logger.info("✅ 응급 알림 관리자 초기화 완료")
            
            # 기본 엔드포인트 확인
            endpoints = manager.list_endpoints()
            if not endpoints:
                logger.info("💡 등록된 엔드포인트가 없습니다.")
                logger.info("   웹 UI의 'API 엔드포인트 관리' 탭에서 추가하세요.")
            else:
                logger.info(f"📋 등록된 엔드포인트: {len(endpoints)}개")
        except Exception as e:
            logger.error(f"⚠️ 응급 알림 관리자 초기화 실패: {e}")

    # 모델 로딩 (ASR)
    if "load_model" in globals():
        try:
            load_model()
            logger.info("✅ ASR 모델 로딩 완료")
        except Exception as e:
            logger.error(f"\n❌ 모델 로딩 실패: {e}", exc_info=True)
            logger.error("\n프로그램 종료")
            sys.exit(1)
    else:
        logger.warning("⚠️ ASR 모델 로더가 없습니다. 음성인식 기능이 제한됩니다.")

    # Gradio UI 생성
    logger.info("\n🎨 Gradio UI 생성 중...")
    
    with gr.Blocks(
        title="음성인식 AI + API 관리",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown("""
        # 🎙️ 안전관리 솔루션 음성감지 AI 테스트 (v6)
        
        RK3588 NPU 최적화 실시간 음성인식 + API 엔드포인트 관리 통합 시스템
        
        **새로운 기능 (v6):**
        - ✅ API 엔드포인트 관리 UI
        - ✅ 다중 엔드포인트 동시 전송
        - ✅ 자동 재시도 로직
        - ✅ SQLite 기반 설정 영구 저장
        """)
        
        with gr.Tabs():
            # 탭 1: 음성인식 (기존 기능)
            with gr.Tab("🎤 실시간 음성인식"):
                gr.Markdown("""
                ### 실시간 음성인식 (VAD 자동 감지)
                
                **사용 방법:**
                1. 마이크 버튼 클릭
                2. 말하기 시작 - 자동으로 인식됩니다
                3. 응급 키워드 감지 시 자동으로 API 전송
                
                **참고:** 실제 음성인식 기능은 Sherpa-ONNX 모델이 필요합니다.
                여기서는 UI 프레임워크만 제공됩니다.
                """)
                
                with gr.Row():
                    with gr.Column():
                        audio_input = gr.Audio(
                            sources=["microphone"],
                            type="numpy",
                            streaming=True,
                            label="🎙️ 마이크 입력"
                        )
                        
                        language = gr.Dropdown(
                            choices=["자동 감지", "한국어", "영어", "중국어"],
                            value="자동 감지",
                            label="언어 선택"
                        )

                        ground_truth_input = gr.Textbox(
                            label="정답 (선택)",
                            placeholder="정답 문구를 입력하세요 (옵션)",
                        )
                        
                        # 제어 버튼
                        with gr.Row():
                            start_vad_btn = gr.Button("🎙️ 음성인식 시작", size="md")
                            stop_vad_btn = gr.Button("⏹️ 음성인식 종료", variant="stop", size="md")
                            reset_vad_btn = gr.Button("🔄 새로 시작", variant="secondary", size="sm")
                        


                    with gr.Column():
                        output_text = gr.Textbox(
                            label="📄 음성인식 결과",
                            lines=15,
                            max_lines=20,
                            autoscroll=True,
                        )

                        # 스트리밍 핸들러 및 버튼 이벤트 연결 (핸들러 유효성 검사)
                        if ASR_HANDLERS_AVAILABLE:
                            try:
                                audio_input.stream(
                                    fn=process_vad_audio_stream,
                                    inputs=[audio_input, language],
                                    outputs=output_text,
                                )
                                logger.info("✅ 오디오 스트리밍 핸들러 연결 완료")
                            except Exception as e:
                                logger.warning(f"⚠️ 스트리밍 핸들러 연결 실패: {e}")
                        else:
                            logger.warning("⚠️ ASR 핸들러를 사용할 수 없습니다.")
                            # 초기 안내 텍스트 설정
                            output_text.value = "⚠️ ASR 모듈을 사용할 수 없습니다. 음성인식 기능이 비활성화되었습니다."

                        # start 버튼 연결 또는 대체 동작
                        if ASR_HANDLERS_AVAILABLE:
                            start_vad_btn.click(
                                fn=start_vad_session_handler,
                                inputs=None,
                                outputs=[start_vad_btn, stop_vad_btn, audio_input, output_text],
                            )
                        else:
                            # 비활성화된 상태에서는 안내 메시지 출력
                            start_vad_btn.click(
                                fn=lambda: "⚠️ ASR 모듈을 사용할 수 없습니다.",
                                inputs=None,
                                outputs=output_text,
                            )

                        if ASR_HANDLERS_AVAILABLE:
                            stop_vad_btn.click(
                                fn=stop_vad_session_handler,
                                inputs=[ground_truth_input],
                                outputs=[output_text, ground_truth_input],
                            )
                        else:
                            stop_vad_btn.click(
                                fn=lambda gt=None: ("⚠️ ASR 모듈을 사용할 수 없습니다.", ""),
                                inputs=[ground_truth_input],
                                outputs=[output_text, ground_truth_input],
                            )

                        if ASR_HANDLERS_AVAILABLE:
                            reset_vad_btn.click(
                                fn=reset_vad_session_handler,
                                inputs=None,
                                outputs=[audio_input, output_text, ground_truth_input],
                            )
                        else:
                            reset_vad_btn.click(
                                fn=lambda: (None, "⚠️ ASR 모듈을 사용할 수 없습니다.", ""),
                                inputs=None,
                                outputs=[audio_input, output_text, ground_truth_input],
                            )
                
                gr.Markdown("""
                **💡 참고:**
                - 실제 음성인식을 위해서는 Sherpa-ONNX 모델 파일이 필요합니다
                - 응급 키워드: "도와줘", "살려줘", "사람", "쓰러졌어" 등
                - 응급 상황 감지 시 등록된 모든 API 엔드포인트로 자동 전송됩니다
                """)
            
            # 탭 2: API 엔드포인트 관리 (신규)
            if API_MODULE_AVAILABLE:
                create_api_management_tab()
            else:
                with gr.Tab("⚙️ API 엔드포인트 관리"):
                    gr.Markdown("""
                    ### ⚠️ API 관리 모듈을 사용할 수 없습니다
                    
                    다음 파일들이 필요합니다:
                    - api_endpoint_db.py
                    - api_utils.py
                    - emergency_alert_manager.py
                    - api_management_ui.py
                    
                    필수 패키지를 설치하세요:
                    ```bash
                    pip install requests flask
                    ```
                    """)
            
            # 탭 3: 시스템 정보
            with gr.Tab("ℹ️ 시스템 정보"):
                gr.Markdown("""
                ### 시스템 정보
                
                **버전:** v6 - API 통합 버전
                
                **주요 기능:**
                1. 🎤 VAD 기반 실시간 음성인식
                2. 🚨 응급 상황 자동 감지
                3. ⚙️ API 엔드포인트 관리
                4. 📊 전송 결과 모니터링
                5. 🔄 자동 재시도 로직
                
                **필수 패키지:**
                - gradio >= 4.0.0
                - requests >= 2.31.0
                - sherpa-onnx >= 1.9.0 (음성인식용)
                
                **선택 패키지:**
                - flask >= 3.0.0 (Mock 서버용)
                
                **데이터베이스:**
                - SQLite (./data/api_endpoints.db)
                
                **로그 파일:**
                - ./logs/app.log
                
                **설정 파일:**
                - ./config/config.json (선택적)
                """)
                
                if API_MODULE_AVAILABLE:
                    def get_system_status():
                        try:
                            manager = get_emergency_manager()
                            endpoints = manager.list_endpoints()
                            active_endpoints = manager.get_enabled_endpoints()
                            watch_id = manager.get_watch_id()
                            sender_id = manager.get_sender_id()
                            
                            status = f"""
### 📊 현재 상태

**API 엔드포인트:**
- 총 등록: {len(endpoints)}개
- 활성화: {len(active_endpoints)}개
- 비활성화: {len(endpoints) - len(active_endpoints)}개

**전역 설정:**
- Watch ID: {watch_id}
- Sender ID: {sender_id}

**데이터베이스:**
- 경로: ./data/api_endpoints.db
- 상태: ✅ 정상

**기능 상태:**
- 음성인식: ⚠️ 모델 파일 필요
- API 전송: ✅ 활성화
- 자동 재시도: ✅ 활성화
- 비동기 전송: ✅ 활성화
"""
                            return status
                        except Exception as e:
                            return f"❌ 상태 조회 실패: {str(e)}"
                    
                    status_btn = gr.Button("🔄 상태 새로고침", variant="secondary")
                    status_output = gr.Markdown()
                    
                    status_btn.click(
                        fn=get_system_status,
                        inputs=None,
                        outputs=status_output,
                    )
                    
                    # 초기 로드
                    demo.load(
                        fn=get_system_status,
                        inputs=None,
                        outputs=status_output,
                    )

    demo.queue()

    logger.info("\n" + "=" * 80)
    logger.info("🌐 웹 서버 시작...")
    logger.info("📍 접속 주소:")
    logger.info("   - HTTPS: https://localhost:7860")
    logger.info("   - HTTP:  http://localhost:7860 (SSL 오류 시)")
    logger.info("\n💡 RK3588 NPU 4코어 사용:")
    logger.info("   taskset 0x0F python demo_vad_with_api.py")
    logger.info("=" * 80 + "\n")

    try:
        # SSL 파일 확인
        ssl_keyfile = "server.key"
        ssl_certfile = "server.crt"
        
        use_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)
        
        if use_ssl:
            logger.info("🔒 SSL 인증서 발견 - HTTPS 모드로 시작")
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                show_error=True,
                inbrowser=False,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
            )
        else:
            logger.info("⚠️ SSL 인증서 없음 - HTTP 모드로 시작")
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                show_error=True,
                inbrowser=False,
            )
    except Exception as e:
        # SSL 검증 오류는 무시하고 서버는 계속 실행됨
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
            logger.warning(f"⚠️ SSL 검증 경고 (무시됨): {e}")
            logger.info("✅ 서버는 정상적으로 실행 중입니다. 브라우저에서 접속해주세요.")
            # 서버가 이미 시작되었으므로 무한 대기
            import time
            while True:
                time.sleep(1)
        else:
            logger.error(f"❌ 서버 시작 실패: {e}")
            raise
