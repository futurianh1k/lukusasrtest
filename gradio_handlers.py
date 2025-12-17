# -*- coding: utf-8 -*-
"""
Gradio UI 핸들러 모듈

Gradio UI의 이벤트 핸들러 함수들
"""

import os
import time
import logging
import gradio as gr
import numpy as np
import soundfile as sf
from datetime import datetime
from typing import Optional

# 상대/절대 import 병행 (스크립트와 패키지 모두 지원)
try:
    # 절대 import (스크립트로 실행할 때)
    from config import LANGUAGE_MAP, GROUND_TRUTHS, LABELS
    from model_loader import recognizer, vad_stream_processor
    from vad_processor import StreamingProcessor
    from session_manager import (
        mic_session_recorder,
        clear_vad_chat_history,
        add_to_vad_chat_history,
        format_vad_chat_history,
    )
    from matcher import SpeechRecognitionMatcher
    from report_generator import generate_mic_session_csv_report, generate_batch_csv_report
    from utils import resample_audio, read_wave
except ImportError:
    # 상대 import (패키지로 실행할 때)
    from .config import LANGUAGE_MAP, GROUND_TRUTHS, LABELS
    from .model_loader import recognizer, vad_stream_processor
    from .vad_processor import StreamingProcessor
    from .session_manager import (
        mic_session_recorder,
        clear_vad_chat_history,
        add_to_vad_chat_history,
        format_vad_chat_history,
    )
    from .matcher import SpeechRecognitionMatcher
    from .emergency_alert import send_emergency_alert
    from .report_generator import generate_mic_session_csv_report, generate_batch_csv_report
    from .utils import resample_audio, read_wave

logger = logging.getLogger(__name__)

# 전역 matcher 인스턴스
matcher = SpeechRecognitionMatcher(GROUND_TRUTHS, LABELS)

# 전역 스트림 프로세서 (레거시)
stream_processor: Optional[StreamingProcessor] = None

# 배치 처리 결과 저장소
batch_results_storage = {
    "file_names": [],
    "ground_truths": [],
    "asr_results": []
}


# ====================
# VAD 기반 핸들러
# ====================

def start_vad_session_handler():
    """음성인식 세션 시작 핸들러 (VAD 기반)"""
    logger.info("=" * 60)
    logger.info("🎤 음성인식 세션 시작 요청")

    if vad_stream_processor is None:
        logger.error("VADStreamingProcessor가 초기화되지 않음")
        return [
            gr.update(interactive=True, value="🎙️ 음성인식 시작"),
            gr.update(interactive=False),
            None,
            "❌ 오류: 음성인식 시스템이 초기화되지 않았습니다."
        ]
    
    # 세션 시작
    success = vad_stream_processor.start_session()
    
    if success:
        session_count = mic_session_recorder.get_session_count()
        status_msg = (
            "🎤 음성인식 세션 활성화!\n\n"
            "✅ 마이크가 계속 켜져 있습니다.\n"
            "✅ 말하기 시작하면 자동으로 인식됩니다.\n"
            "✅ VAD가 음성을 자동 감지합니다.\n\n"
            "🔴 음성인식 종료 버튼을 눌러 세션을 종료하세요.\n\n"
            f"📊 이전 저장된 세션: {session_count}개"
        )
        
        logger.info("✅ 음성인식 세션 시작 성공")
        logger.info("=" * 60)
        
        return [
            gr.update(interactive=False, value="🔴 음성인식 세션 활성화 중..."),
            gr.update(interactive=True),
            None,
            status_msg
        ]
    else:
        return [
            gr.update(interactive=True, value="🎙️ 음성인식 시작"),
            gr.update(interactive=False),
            None,
            "⚠️ 세션을 시작할 수 없습니다. 다시 시도해주세요."
        ]


def stop_vad_session_handler(ground_truth_input):
    """음성인식 세션 종료 핸들러 (VAD 기반)"""
    logger.info("⏹️ 음성인식 세션 종료 요청")

    if vad_stream_processor is None:
        logger.error("VADStreamingProcessor가 None")
        return [
            "⚠️ 음성인식 세션이 없습니다.",
            ""
        ]

    # 세션 종료
    session_result = vad_stream_processor.stop_session()
    
    if session_result:
        segments = session_result.get('segments', [])
        total_segments = session_result.get('total_segments', 0)
        total_duration = session_result.get('total_duration', 0)
        
        # 각 구간에 대한 응급 상황 체크
        emergency_detected = False
        emergency_segments = []
        
        result_text = f"⏹️ 음성인식 세션 종료\n\n"
        result_text += f"📊 세션 통계:\n"
        result_text += f"   - 감지된 음성 구간: {total_segments}개\n"
        result_text += f"   - 총 음성 길이: {total_duration:.1f}초\n\n"
        
        if segments:
            result_text += "📝 인식 결과:\n"
            result_text += "=" * 60 + "\n\n"
            
            for idx, seg in enumerate(segments, 1):
                text = seg.get('text', '')
                timestamp = seg.get('timestamp', '')
                duration = seg.get('duration', 0)
                
                result_text += f"[{idx}] {timestamp} ({duration:.1f}초)\n"
                result_text += f"    {text}\n\n"
                
                # 응급 상황 체크
                match_result = matcher.find_best_match(text)
                if match_result.get("is_emergency", False):
                    emergency_detected = True
                    emergency_keywords = match_result.get("emergency_keywords", [])
                    emergency_segments.append({
                        'index': idx,
                        'text': text,
                        'keywords': emergency_keywords,
                        'timestamp': timestamp
                    })
                    
                    logger.warning(f"🚨 응급 상황 감지 [구간 {idx}]: {emergency_keywords}")
        else:
            result_text += "⚠️ 인식된 음성이 없습니다.\n"
        
        # 응급 상황 요약
        if emergency_detected:
            result_text += "\n" + "=" * 60 + "\n"
            result_text += "🚨🚨🚨 응급 상황 감지됨! 🚨🚨🚨\n\n"
            for emerg in emergency_segments:
                result_text += f"[구간 {emerg['index']}] {emerg['timestamp']}\n"
                result_text += f"   키워드: {', '.join(emerg['keywords'])}\n"
                result_text += f"   내용: {emerg['text']}\n\n"
            result_text += "✅ 응급 알림이 전송되었습니다.\n"
        
        # 세션 결과 저장 (전체 텍스트 합침)
        if segments:
            combined_text = " ".join([seg.get('text', '') for seg in segments])
            gt = ground_truth_input.strip() if ground_truth_input else "(정답 미입력)"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            mic_session_recorder.add_session_result(
                ground_truth=gt,
                asr_result=combined_text,
                duration=total_duration,
                timestamp=timestamp
            )
        
        session_count = mic_session_recorder.get_session_count()
        result_text += f"\n📊 현재 저장된 세션: {session_count}개"
        
        # 채팅 히스토리 초기화
        clear_vad_chat_history()
        
        logger.info("✅ 음성인식 세션 종료 완료")
        
        return [
            result_text,
            ""  # ground_truth 초기화
        ]
    else:
        session_count = mic_session_recorder.get_session_count()
        clear_vad_chat_history()
        
        return [
            f"⏹️ 세션 종료\n\n⚠️ 활성화된 세션이 없었습니다.\n\n📊 현재 저장된 세션: {session_count}개",
            ""
        ]


def reset_vad_session_handler():
    """VAD 세션 리셋 핸들러"""
    logger.info("🔄 VAD 세션 리셋 요청")

    if vad_stream_processor is None:
        return [
            None,
            "⚠️ 음성인식 시스템이 초기화되지 않았습니다.",
            ""
        ]
    
    vad_stream_processor.reset()
    clear_vad_chat_history()
    session_count = mic_session_recorder.get_session_count()
    
    return [
        None,  # audio 컴포넌트 리셋
        f"🔄 세션이 초기화되었습니다.\n\n마이크 버튼을 다시 클릭하여 시작하세요.\n\n📊 저장된 세션: {session_count}개",
        ""  # ground_truth 초기화
    ]


def process_vad_audio_stream(audio_stream, language):
    """VAD 기반 마이크 스트리밍 오디오 처리"""
    if audio_stream is None:
        yield ""
        return

    try:
        sr, audio_data = audio_stream

        if audio_data is None or len(audio_data) == 0:
            yield ""
            return

        # 스테레오 → 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # float32 정규화
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # 16kHz 리샘플링
        if sr != 16000:
            audio_data = resample_audio(audio_data, sr, 16000)

        # 프로세서 확인
        if not vad_stream_processor:
            yield ""
            return

        # 세션이 활성화되지 않았으면 자동 시작
        status = vad_stream_processor.get_session_status()
        if not status['is_active']:
            logger.info("🎤 오디오 스트림 감지 - 자동으로 세션 시작")
            vad_stream_processor.start_session()
            clear_vad_chat_history()
            
            session_count = mic_session_recorder.get_session_count()
            yield (
                "🎤 음성인식 자동 시작!\n\n"
                "✅ 말하기 시작하면 자동으로 인식됩니다.\n\n"
                "🗣️ 지금 말씀해주세요...\n\n"
                f"📊 저장된 세션: {session_count}개"
            )
            status = vad_stream_processor.get_session_status()

        # 오디오 청크 처리 (VAD 기반)
        result = vad_stream_processor.add_audio_chunk(audio_data)
        
        segments_count = status['segments_count']
        is_processing = status['is_processing']
        
        if result:
            # 새로운 음성 구간 인식 완료
            text = result.get('text', '')
            duration = result.get('duration', 0)
            timestamp = result.get('timestamp', '')
            
            # 응급 상황 실시간 체크
            match_result = matcher.find_best_match(text)
            is_emergency = False
            emergency_keywords = []
            
            if match_result.get("is_emergency", False):
                    is_emergency = True
                    emergency_keywords = match_result.get("emergency_keywords", [])
                    logger.warning(f"🚨 실시간 응급 상황 감지! 키워드: {emergency_keywords}")

                    # API 호출 (모듈을 런타임에 안전하게 import)
                    try:
                        from emergency_alert import send_emergency_alert
                    except Exception:
                        try:
                            from .emergency_alert import send_emergency_alert
                        except Exception as e:
                            logger.warning(f"⚠️ send_emergency_alert import 실패: {e}")
                            send_emergency_alert = None
                    if send_emergency_alert:
                        send_emergency_alert(text, emergency_keywords)
                    else:
                        logger.info("ℹ️ 응급 알림 모듈이 없어 전송을 건너뜁니다.")
            # 채팅 히스토리에 추가
            add_to_vad_chat_history(timestamp, text, duration, is_emergency, emergency_keywords)
            
            # 누적된 히스토리 포맷팅하여 출력
            output = format_vad_chat_history()
            
            logger.info(f"🎤 VAD 인식 완료: {text}")
            yield output
        else:
            # 처리 중이거나 대기 중일 때
            # format_vad_chat_history()는 내부에서 vad_chat_history를 확인함
            output = format_vad_chat_history()
            
            if output != "👂 대기 중... 말씀해주세요.":
                # 히스토리가 있는 경우
                if is_processing:
                    output += "\n\n🗣️ 음성 감지 중... 처리 중입니다."
                
                yield output
            else:
                # 히스토리가 없는 경우
                if is_processing:
                    yield (
                        "🔴 음성인식 세션 활성화 중...\n\n"
                        "🗣️ 음성 감지 중... 처리 중입니다."
                    )
                else:
                    yield output  # "👂 대기 중... 말씀해주세요."

    except Exception as e:
        logger.error(f"❌ VAD 오디오 처리 오류: {e}", exc_info=True)
        yield f"❌ 오류: {str(e)}"


# ====================
# 레거시 핸들러
# ====================

def start_recording_handler():
    """녹음 시작 버튼 핸들러 (레거시)"""
    global stream_processor

    logger.info("=" * 60)
    logger.info("🟡 녹음 시작 버튼 클릭")

    if stream_processor is not None:
        logger.debug("기존 StreamingProcessor 재사용")
        stream_processor.prepare()
    else:
        logger.warning("StreamingProcessor가 None, 새로 생성")
        stream_processor = StreamingProcessor(recognizer, chunk_duration=20.0)
        stream_processor.prepare()

    logger.info(f"✅ 녹음 준비 완료: is_ready={stream_processor.is_ready}, is_recording={stream_processor.is_recording}")
    logger.info("=" * 60)

    session_count = mic_session_recorder.get_session_count()
    status_msg = f"🟡 준비 완료!\n\n마이크 버튼(🎤)을 눌러 녹음을 시작하세요.\n2초마다 실시간 인식됩니다.\n\n📊 현재 저장된 세션: {session_count}개"

    return [
        gr.update(interactive=False, value="🟡 준비 완료 - 마이크 버튼을 눌러주세요"),
        gr.update(interactive=True),
        None,  # Audio 컴포넌트 리셋
        status_msg
    ]


def stop_recording_handler(ground_truth_input):
    """녹음 종료 버튼 핸들러"""
    global stream_processor

    logger.info("⏹️ 녹음 종료 버튼 클릭")

    if stream_processor is None:
        logger.error("StreamingProcessor가 None")
        return [
            gr.update(interactive=True, value="🎙️ 녹음 시작"),
            gr.update(interactive=False),
            "⚠️ 녹음 세션이 없습니다.",
            ""  # ground_truth 초기화
        ]

    logger.debug(f"종료 전 상태: is_ready={stream_processor.is_ready}, is_recording={stream_processor.is_recording}")

    if stream_processor.is_ready and not stream_processor.is_recording:
        logger.warning("마이크 버튼을 누르지 않은 상태에서 종료")
        stream_processor.reset()
        session_count = mic_session_recorder.get_session_count()
        return [
            gr.update(interactive=True, value="🎙️ 녹음 시작"),
            gr.update(interactive=False),
            f"⚠️ 마이크 버튼을 누르지 않아 녹음되지 않았습니다.\n\n📊 현재 저장된 세션: {session_count}개",
            ""  # ground_truth 초기화
        ]

    # 정상 녹음 종료
    final_text = stream_processor.stop_recording()
    duration = stream_processor.get_current_duration()

    if final_text:
        # 세션 결과 저장
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        gt = ground_truth_input.strip() if ground_truth_input else "(정답 미입력)"

        mic_session_recorder.add_session_result(
            ground_truth=gt,
            asr_result=final_text,
            duration=duration,
            timestamp=timestamp
        )

        match_result = matcher.find_best_match(final_text)
        logger.info(f"⏹️ 최종 결과 ({duration:.1f}초): {match_result}")

        # 응급 상황 감지 시 API 호출
        if match_result.get("is_emergency", False):
            emergency_keywords = match_result.get("emergency_keywords", [])
            logger.warning(f"🚨 응급 상황 감지됨! 키워드: {emergency_keywords}")
            try:
                from emergency_alert import send_emergency_alert
            except Exception:
                try:
                    from .emergency_alert import send_emergency_alert
                except Exception as e:
                    logger.warning(f"⚠️ send_emergency_alert import 실패: {e}")
                    send_emergency_alert = None
            if send_emergency_alert:
                send_emergency_alert(final_text, emergency_keywords)
            else:
                logger.info("ℹ️ 응급 알림 모듈이 없어 전송을 건너뜁니다.")

        session_count = mic_session_recorder.get_session_count()

        return [
            gr.update(interactive=True, value="🎙️ 녹음 시작"),
            gr.update(interactive=False),
            f"⏹️ 녹음 종료 ({duration:.1f}초)\n\n✅ 최종 결과:\n{final_text}\n\n📊 현재 저장된 세션: {session_count}개",
            ""  # ground_truth 초기화
        ]
    else:
        logger.warning("인식된 텍스트 없음")
        session_count = mic_session_recorder.get_session_count()
        return [
            gr.update(interactive=True, value="🎙️ 녹음 시작"),
            gr.update(interactive=False),
            f"⏹️ 녹음 종료\n\n⚠️ 인식된 텍스트가 없습니다.\n\n📊 현재 저장된 세션: {session_count}개",
            ""  # ground_truth 초기화
        ]


def collect_and_process_audio(audio_stream, language):
    """마이크 스트리밍 오디오 수집 및 실시간 처리 (레거시)"""
    global stream_processor

    if audio_stream is None:
        yield ""
        return

    try:
        sr, audio_data = audio_stream

        if audio_data is None or len(audio_data) == 0:
            yield ""
            return

        logger.debug(f"오디오 수신: {len(audio_data)} samples, {sr}Hz")

        # 스테레오 → 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
            logger.debug("스테레오 → 모노 변환")

        # float32 정규화
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # 16kHz 리샘플링
        if sr != 16000:
            audio_data = resample_audio(audio_data, sr, 16000)
            logger.debug(f"리샘플링: {sr}Hz → 16000Hz")

        # 프로세서 준비 확인
        if not stream_processor or not stream_processor.is_ready:
            logger.debug(f"프로세서 준비 안 됨")
            yield ""
            return

        # 오디오 청크 처리
        result_text = stream_processor.add_audio_chunk(audio_data)
        duration = stream_processor.get_current_duration()

        if result_text:
            match_result = matcher.find_best_match(result_text)
            logger.info(f"🎤 실시간 인식 ({duration:.1f}초): {match_result}")
            
            # 응급 상황 감지 시 API 호출
            if match_result.get("is_emergency", False):
                emergency_keywords = match_result.get("emergency_keywords", [])
                logger.warning(f"🚨 실시간 응급 상황 감지됨! 키워드: {emergency_keywords}")
                try:
                    from emergency_alert import send_emergency_alert
                except Exception:
                    try:
                        from .emergency_alert import send_emergency_alert
                    except Exception as e:
                        logger.warning(f"⚠️ send_emergency_alert import 실패: {e}")
                        send_emergency_alert = None
                if send_emergency_alert:
                    send_emergency_alert(result_text, emergency_keywords)
                else:
                    logger.info("ℹ️ 응급 알림 모듈이 없어 전송을 건너뜁니다.")
            
            yield f"🔴 녹음 중... ({duration:.1f}초)\n\n✅ 실시간 인식:\n{result_text}"
        else:
            last = stream_processor.last_result
            if last:
                yield f"🔴 녹음 중... ({duration:.1f}초)\n\n✅ 현재 인식:\n{last}"
            else:
                if stream_processor.is_recording:
                    yield f"🔴 녹음 중... ({duration:.1f}초)\n\n대기 중..."
                else:
                    yield ""

    except Exception as e:
        logger.error(f"❌ 오디오 처리 오류: {e}", exc_info=True)
        yield f"❌ 오류: {str(e)}"


# ====================
# 파일 처리 핸들러
# ====================

def _resolve_file_path(audio_file):
    """파일 경로 추출"""
    if isinstance(audio_file, dict):
        return audio_file.get("path") or audio_file.get("name")
    if hasattr(audio_file, "name"):
        return audio_file.name
    return audio_file


def transcribe_file(audio_file, language):
    """파일 업로드 음성인식"""
    start_time = time.time()

    try:
        if audio_file is None:
            return "⚠️ 파일을 업로드해주세요."

        file_path = _resolve_file_path(audio_file)
        if not file_path or not os.path.exists(file_path):
            return f"❌ 파일 경로 오류: {file_path}"

        logger.info(f"⏱️ 파일 처리 시작: {file_path}")

        # 파일 읽기
        try:
            audio_data, sr = sf.read(file_path)
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            samples = audio_data.astype(np.float32)
            sample_rate = sr
        except Exception as e1:
            logger.warning(f"soundfile 실패: {e1}, wave 시도")
            try:
                samples, sample_rate = read_wave(file_path)
            except Exception as e2:
                raise Exception(f"파일 읽기 실패. soundfile: {e1}, wave: {e2}")

        # 16kHz 리샘플링
        if sample_rate != 16000:
            logger.info(f"🔄 리샘플링: {sample_rate} Hz → 16000 Hz")
            samples = resample_audio(samples, sample_rate, 16000)
            sample_rate = 16000

        duration = len(samples) / sample_rate
        logger.info(f"🎤 음성인식 시작 - 길이: {duration:.2f}초")

        # Offline Recognizer로 처리
        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        recognizer.decode_stream(stream)
        result = stream.result

        text = result.text.strip()

        # 정답 매칭
        match_result = matcher.find_best_match(text)

        if not text:
            text = "⚠️ 음성을 인식하지 못했습니다."

        file_name = os.path.basename(file_path)
        logger.info(f"📁 {file_name}\n{match_result}\n")

        total_time = time.time() - start_time
        logger.info(f"✅ 변환 완료: {text}")
        logger.info(f"⏱️ 처리 시간: {total_time:.2f}초")

        return text

    except Exception as e:
        logger.error(f"파일 처리 오류: {e}", exc_info=True)
        return f"❌ 오류: {str(e)}"


def batch_transcribe(files, language):
    """배치 파일 처리"""
    global batch_results_storage

    if not files:
        return "⚠️ 파일을 업로드해주세요."

    # 결과 초기화
    batch_results_storage = {
        "file_names": [],
        "ground_truths": [],
        "asr_results": []
    }

    results = []
    total = len(files)

    for idx, file in enumerate(files, 1):
        try:
            file_path = _resolve_file_path(file)
            file_name = os.path.basename(file_path)
            logger.info(f"[{idx}/{total}] 처리 중: {file_name}")

            # 파일 읽기
            try:
                audio_data, sr = sf.read(file_path)
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                samples = audio_data.astype(np.float32)
                sample_rate = sr
            except Exception:
                try:
                    samples, sample_rate = read_wave(file_path)
                except Exception as e:
                    raise Exception(f"파일 읽기 실패: {e}")

            if sample_rate != 16000:
                samples = resample_audio(samples, sample_rate, 16000)
                sample_rate = 16000

            # Offline 처리
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            recognizer.decode_stream(stream)
            result = stream.result
            text = result.text.strip()

            # 정답 매칭
            match_result = matcher.find_best_match(text)
            best_match = match_result.get("best_match", "")

            if not text:
                text = "(음성 인식 실패)"

            # 결과 저장
            batch_results_storage["file_names"].append(file_name)
            batch_results_storage["ground_truths"].append(best_match)
            batch_results_storage["asr_results"].append(text)

            results.append(f"📁 **{file_name}**\n{text}\n")
            logger.info(f"📁 **{file_name}**\n{match_result}\n")

        except Exception as e:
            results.append(f"📁 **{file_name}**\n❌ 오류: {str(e)}\n")
            logger.error(f"파일 처리 실패: {file_name} - {e}")

            # 오류 발생 시에도 저장
            batch_results_storage["file_names"].append(file_name)
            batch_results_storage["ground_truths"].append("")
            batch_results_storage["asr_results"].append(f"ERROR: {str(e)}")

    output = f"✅ 총 {total}개 파일 처리 완료\n\n" + "\n".join(results)
    return output


# ====================
# CSV 리포트 핸들러
# ====================

def generate_mic_csv_handler():
    """마이크 세션 CSV 리포트 생성 핸들러"""
    sessions = mic_session_recorder.get_all_sessions()

    if not sessions:
        return None, "⚠️ 생성할 세션 결과가 없습니다. 먼저 녹음 테스트를 진행해주세요."

    # CSV 생성
    csv_path = generate_mic_session_csv_report(sessions, matcher)

    if csv_path and os.path.exists(csv_path):
        return csv_path, f"✅ CSV 리포트 생성 완료!\n\n📊 총 {len(sessions)}개 세션 처리\n📁 파일: {csv_path}"
    else:
        return None, "❌ CSV 리포트 생성 실패"


def clear_mic_sessions_handler():
    """마이크 세션 결과 초기화 핸들러"""
    mic_session_recorder.clear_sessions()
    return "✅ 모든 세션 결과가 초기화되었습니다.\n\n새로운 테스트를 시작하세요."


def generate_batch_csv_handler():
    """배치 테스트 CSV 리포트 생성 핸들러"""
    if not batch_results_storage["file_names"]:
        return None, "⚠️ 생성할 배치 테스트 결과가 없습니다. 먼저 배치 변환을 진행해주세요."

    # CSV 생성
    csv_path = generate_batch_csv_report(
        file_names=batch_results_storage["file_names"],
        ground_truths=batch_results_storage["ground_truths"],
        asr_results=batch_results_storage["asr_results"],
        matcher=matcher
    )

    if csv_path and os.path.exists(csv_path):
        count = len(batch_results_storage["file_names"])
        return csv_path, f"✅ CSV 리포트 생성 완료!\n\n📊 총 {count}개 파일 처리\n📁 파일: {csv_path}"
    else:
        return None, "❌ CSV 리포트 생성 실패"

