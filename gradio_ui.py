# -*- coding: utf-8 -*-
"""
Gradio UI 생성 모듈

Gradio 웹 UI 생성 및 설정
"""

import logging
import gradio as gr

# 패키지 외부에서 실행 가능하도록 try-except 처리
try:
    # 패키지 내부에서 실행 시 (상대 import)
    from .gradio_handlers import (
        start_vad_session_handler,
        stop_vad_session_handler,
        reset_vad_session_handler,
        process_vad_audio_stream,
        start_recording_handler,
        stop_recording_handler,
        collect_and_process_audio,
        transcribe_file,
        batch_transcribe,
        generate_mic_csv_handler,
        clear_mic_sessions_handler,
        generate_batch_csv_handler,
    )
except ImportError:
    # 패키지 외부에서 직접 실행 시 (절대 import)
    from gradio_handlers import (
        start_vad_session_handler,
        stop_vad_session_handler,
        reset_vad_session_handler,
        process_vad_audio_stream,
        start_recording_handler,
        stop_recording_handler,
        collect_and_process_audio,
        transcribe_file,
        batch_transcribe,
        generate_mic_csv_handler,
        clear_mic_sessions_handler,
        generate_batch_csv_handler,
    )

logger = logging.getLogger(__name__)


def create_ui():
    """Gradio UI 생성"""

    css = """
    /* 출력 박스 스타일 - 채팅 스타일 */
    .output-box textarea {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.8;
        overflow-y: auto !important;
        max-height: 600px;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    /* 스크롤바 스타일 */
    .output-box textarea::-webkit-scrollbar {
        width: 12px;
    }
    
    .output-box textarea::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .output-box textarea::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    
    .output-box textarea::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    """

    with gr.Blocks(
        title="안전관리 솔루션 음성감지 AI 테스트",
        css=css,
    ) as demo:
        gr.Markdown("""
        # 🎙️ 안전관리 솔루션 음성감지 AI 테스트

        RK3588 NPU 최적화 실시간 음성인식 시스템 (v4 - CSV 리포트 기능 추가)
        """)

        with gr.Tabs():
            # 탭 1: VAD 기반 실시간 음성인식
            with gr.Tab("🎤 실시간 음성인식 (VAD)"):
                gr.Markdown("""
                ### VAD 기반 실시간 음성인식 시스템 (v5 - VAD 자동 감지)

                🔧 **v5 신규 기능**:
                - ✅ **VAD (Voice Activity Detection)** - 음성 자동 감지
                - ✅ **간편한 사용** - 마이크 버튼만 클릭하면 자동 인식 시작
                - ✅ **자동 ASR-STT** - 음성 감지 시 자동으로 인식
                - ✅ **응급 상황 실시간 감지** - 키워드 기반 즉시 알림
                - ✅ 세션별 CSV 리포트 자동 생성
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("""
                        ### 🎤 마이크 입력
                        
                        **사용 방법:**
                        1. 아래 마이크 버튼(🎤) 클릭
                        2. 말하기 시작 - 자동으로 인식됩니다
                        3. 침묵하면 자동으로 다음 음성 대기
                        4. 종료하려면 "음성인식 종료" 버튼 클릭
                        """)
                        
                        audio_stream_vad = gr.Audio(
                            sources=["microphone"],
                            type="numpy",
                            streaming=True,
                            label="🎙️ 마이크 (클릭하여 시작)",
                        )

                        language_stream_vad = gr.Dropdown(
                            choices=["자동 감지", "한국어", "중국어", "영어", "일본어", "광동어"],
                            value="자동 감지",
                            label="🌐 언어 선택",
                        )

                        ground_truth_input_vad = gr.Textbox(
                            label="📝 정답 (Ground Truth) 입력 (선택사항)",
                            placeholder="예: 도와줘 사람이 쓰러졌어",
                            lines=2
                        )

                        with gr.Row():
                            stop_vad_btn = gr.Button("⏹️ 음성인식 종료", variant="stop", size="lg")
                            reset_vad_btn = gr.Button("🔄 새로 시작", variant="secondary", size="sm")

                    with gr.Column(scale=1):
                        output_stream_vad = gr.Textbox(
                            label="📄 실시간 음성인식 결과 (채팅 스타일)",
                            lines=20,
                            max_lines=30,
                            elem_classes="output-box",
                            autoscroll=True,
                            show_copy_button=True,
                        )

                gr.Markdown("### 📊 세션 관리 및 CSV 리포트")

                with gr.Row():
                    generate_csv_btn_vad = gr.Button("📥 CSV 리포트 생성", variant="secondary", size="lg")
                    clear_sessions_btn_vad = gr.Button("🗑️ 세션 초기화", variant="stop", size="sm")

                csv_output_file_vad = gr.File(label="📁 생성된 CSV 파일")
                csv_status_vad = gr.Textbox(label="📊 CSV 생성 상태", lines=3)

                gr.Markdown("""
                #### 💡 간편한 사용법
                1. 🎤 **마이크 버튼 클릭** → 녹음 시작 (브라우저가 마이크 권한 요청)
                2. 🗣️ **말하기** → VAD가 자동 감지하여 실시간 인식
                3. 🔇 **잠시 침묵** → 자동으로 구간 구분 및 결과 표시
                4. 🔄 **계속 말하기** → 여러 구간 연속 인식 가능
                5. ⏹️ **"음성인식 종료"** → 세션 종료 및 전체 결과 확인
                6. 📝 **(선택) 정답 입력** → CSV 리포트 생성 시 활용
                
                #### ⚡ v5 특징 (VAD 기반)
                - 🎯 **완전 자동** - 마이크만 클릭하면 자동으로 음성 감지 시작
                - ⏱️ **실시간 표시** - 음성 구간마다 즉시 결과 화면 표시
                - 🚨 **응급 즉시 알림** - 응급 키워드 감지 시 API 자동 호출
                - 📊 **구간별 저장** - 각 음성 구간 개별 저장 및 관리
                - 🔇 **자동 구간 분리** - 침묵 1.5초 감지로 자동 구간 구분
                
                #### ⚙️ 조정 가능한 설정
                - **에너지 임계값**: 0.01 (낮을수록 작은 소리도 감지)
                - **침묵 판단**: 1.5초 (침묵으로 인식하는 시간)
                - **최소 음성 길이**: 0.5초 (이보다 짧으면 무시)
                """)

                # 오디오 스트림 처리
                audio_stream_vad.stream(
                    fn=process_vad_audio_stream,
                    inputs=[audio_stream_vad, language_stream_vad],
                    outputs=output_stream_vad,
                )

                stop_vad_btn.click(
                    fn=stop_vad_session_handler,
                    inputs=[ground_truth_input_vad],
                    outputs=[output_stream_vad, ground_truth_input_vad],
                )
                
                reset_vad_btn.click(
                    fn=reset_vad_session_handler,
                    inputs=None,
                    outputs=[audio_stream_vad, output_stream_vad, ground_truth_input_vad],
                )

                generate_csv_btn_vad.click(
                    fn=generate_mic_csv_handler,
                    inputs=None,
                    outputs=[csv_output_file_vad, csv_status_vad]
                )

                clear_sessions_btn_vad.click(
                    fn=clear_mic_sessions_handler,
                    inputs=None,
                    outputs=csv_status_vad
                )

            # 탭 2: 기존 방식 (레거시)
            with gr.Tab("🎤 실시간 음성인식 (기존 방식)"):
                gr.Markdown("""
                ### 실시간 스트리밍 음성인식 (v4 - 기존 방식)

                🔧 **v4 기능**:
                - ✅ 마이크 세션 결과 자동 누적 저장
                - ✅ 세션별 CSV 리포트 자동 생성
                - ✅ 세션 결과 초기화 기능
                - ✅ 정답(Ground Truth) 입력 지원
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        audio_stream = gr.Audio(
                            sources=["microphone"],
                            type="numpy",
                            streaming=True,
                            label="🎙️ 마이크 (실시간 수집)",
                        )

                        language_stream = gr.Dropdown(
                            choices=["자동 감지", "한국어", "중국어", "영어", "일본어", "광동어"],
                            value="자동 감지",
                            label="🌐 언어 선택",
                        )

                        ground_truth_input = gr.Textbox(
                            label="📝 정답 (Ground Truth) 입력 (선택사항)",
                            placeholder="예: 회의는 오후 세 시에 시작해 알림 설정해 줘",
                            lines=2
                        )

                        with gr.Row():
                            start_btn = gr.Button("🎙️ 녹음 시작", variant="primary", size="lg")
                            stop_btn = gr.Button("⏹️ 녹음 종료", variant="stop", size="lg")

                    with gr.Column(scale=1):
                        output_stream = gr.Textbox(
                            label="📄 실시간 음성인식 결과",
                            lines=15,
                            elem_classes="output-box",
                        )

                gr.Markdown("### 📊 세션 관리 및 CSV 리포트")

                with gr.Row():
                    generate_csv_btn = gr.Button("📥 CSV 리포트 생성", variant="secondary", size="lg")
                    clear_sessions_btn = gr.Button("🗑️ 세션 초기화", variant="stop", size="sm")

                csv_output_file = gr.File(label="📁 생성된 CSV 파일")
                csv_status = gr.Textbox(label="📊 CSV 생성 상태", lines=3)

                gr.Markdown("""
                #### 💡 사용 방법
                1. 🟡 **"녹음 시작" 버튼 클릭** → 준비 완료
                2. 📝 **(선택) 정답(Ground Truth) 입력** → CSV 리포트에 사용
                3. 🎤 **마이크 버튼 클릭** → 자동 녹음 시작
                4. 🗣️ **말하기** → 2초마다 실시간 인식
                5. ⏹️ **"녹음 종료" 버튼 클릭** → 결과 저장 및 최종 결과 표시
                6. 🔄 **반복 테스트 가능** → 여러 세션 누적 저장
                7. 📥 **"CSV 리포트 생성" 클릭** → 모든 세션 결과를 CSV 파일로 저장
                8. 🗑️ **"세션 초기화" 클릭** → 저장된 모든 세션 결과 삭제

                #### ⚡ v4 특징
                - ✅ 세션별 결과 자동 누적 (메모리 효율적)
                - ✅ CER(Character Error Rate) 자동 계산
                - ✅ CSV 파일 다운로드 지원
                - ✅ 정답 입력으로 정확한 평가 가능
                """)

                start_btn.click(
                    fn=start_recording_handler,
                    inputs=None,
                    outputs=[start_btn, stop_btn, audio_stream, output_stream],
                )

                stop_btn.click(
                    fn=stop_recording_handler,
                    inputs=[ground_truth_input],
                    outputs=[start_btn, stop_btn, output_stream, ground_truth_input],
                )

                audio_stream.stream(
                    fn=collect_and_process_audio,
                    inputs=[audio_stream, language_stream],
                    outputs=output_stream,
                )

                generate_csv_btn.click(
                    fn=generate_mic_csv_handler,
                    inputs=None,
                    outputs=[csv_output_file, csv_status]
                )

                clear_sessions_btn.click(
                    fn=clear_mic_sessions_handler,
                    inputs=None,
                    outputs=csv_status
                )

            # 탭 3: 파일 업로드
            with gr.Tab("📁 파일 업로드"):
                gr.Markdown("### 오디오 파일 업로드\nWAV, MP3, FLAC, M4A 등 지원")

                with gr.Row():
                    with gr.Column(scale=1):
                        audio_file = gr.File(
                            label="📁 오디오 파일 업로드",
                            file_types=["audio"],
                        )

                        language_file = gr.Dropdown(
                            choices=["자동 감지", "한국어", "중국어", "영어", "일본어", "광동어"],
                            value="자동 감지",
                            label="🌐 언어 선택",
                        )

                        transcribe_btn = gr.Button("🚀 변환 시작", variant="primary", size="lg")
                        clear_btn = gr.Button("🗑️ 초기화", size="sm")

                    with gr.Column(scale=1):
                        output_file = gr.Textbox(
                            label="📄 변환 결과",
                            lines=15,
                            elem_classes="output-box",
                        )

                transcribe_btn.click(
                    fn=transcribe_file,
                    inputs=[audio_file, language_file],
                    outputs=output_file,
                )

                clear_btn.click(
                    fn=lambda: (None, ""),
                    outputs=[audio_file, output_file],
                )

            # 탭 4: 배치 처리 (CSV 생성 기능 통합)
            with gr.Tab("📦 배치 변환"):
                gr.Markdown("""
                ### 📥 여러 파일 일괄 처리 및 CSV 리포트 생성

                🔧 **v4 신규 기능**:
                - ✅ 배치 처리 결과 자동 저장
                - ✅ CSV 리포트 자동 생성 (CER 포함)
                """)

                with gr.Row():
                    with gr.Column():
                        batch_files = gr.File(
                            file_count="multiple",
                            label="오디오 파일들을 선택하세요",
                            file_types=["audio"],
                        )

                        batch_language = gr.Dropdown(
                            choices=["자동 감지", "한국어", "중국어", "영어", "일본어", "광동어"],
                            value="자동 감지",
                            label="🌐 언어 선택",
                        )

                        batch_btn = gr.Button("🚀 일괄 변환", variant="primary", size="lg")

                    with gr.Column():
                        batch_output = gr.Textbox(
                            label="📄 일괄 변환 결과",
                            lines=20,
                        )

                gr.Markdown("### 📊 배치 테스트 CSV 리포트")

                generate_batch_csv_btn = gr.Button("📥 CSV 리포트 생성", variant="secondary", size="lg")

                batch_csv_output_file = gr.File(label="📁 생성된 CSV 파일")
                batch_csv_status = gr.Textbox(label="📊 CSV 생성 상태", lines=3)

                batch_btn.click(
                    fn=batch_transcribe,
                    inputs=[batch_files, batch_language],
                    outputs=batch_output,
                )

                generate_batch_csv_btn.click(
                    fn=generate_batch_csv_handler,
                    inputs=None,
                    outputs=[batch_csv_output_file, batch_csv_status]
                )

        gr.Markdown("""
        ---
        <div style="text-align: center; color: #666; padding: 20px;">
            Powered by Sherpa-ONNX + Gradio | RK3588 NPU | v4 (CSV 리포트 기능 추가)
        </div>
        """)

    return demo

