# -*- coding: utf-8 -*-
"""
VAD (Voice Activity Detection) 프로세서 모듈

실시간 음성인식을 위한 VAD 기반 스트리밍 프로세서
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Optional
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class VADStreamingProcessor:
    """에너지 기반 간단한 VAD를 사용한 실시간 음성인식 프로세서"""

    def __init__(self, recognizer, sample_rate=16000, vad_enabled=True):
        self.recognizer = recognizer
        self.sample_rate = sample_rate
        
        # 간단한 에너지 기반 VAD 설정
        self.vad_enabled = vad_enabled
        self.energy_threshold = 0.01  # 에너지 임계값 (조정 가능)
        self.silence_duration = 1.5  # 침묵 판단 시간 (초)
        self.min_speech_duration = 0.5  # 최소 음성 길이 (초)
        
        # 음성 버퍼
        self.audio_buffer = deque()
        self.speech_segments = []  # 음성 구간 저장
        
        # 상태 관리
        self.is_session_active = False  # 세션 활성화 상태
        self.is_processing = False  # 음성 처리 중
        self.silence_frames = 0  # 침묵 프레임 카운터
        self.speech_frames = 0  # 음성 프레임 카운터
        self.last_result = ""
        self.lock = threading.Lock()
        
        logger.info(f"✅ VADStreamingProcessor 초기화 완료")
        logger.info(f"   - VAD: 에너지 기반 간단한 VAD")
        logger.info(f"   - 에너지 임계값: {self.energy_threshold}")
        logger.info(f"   - 침묵 감지: {self.silence_duration}초")

    def _calculate_energy(self, audio_chunk: np.ndarray) -> float:
        """오디오 청크의 에너지 계산 (RMS)"""
        return np.sqrt(np.mean(audio_chunk ** 2))

    def _is_speech(self, audio_chunk: np.ndarray) -> bool:
        """에너지 기반 음성 감지"""
        if not self.vad_enabled:
            return True
        
        energy = self._calculate_energy(audio_chunk)
        return energy > self.energy_threshold

    def start_session(self):
        """음성인식 세션 시작 (마이크 계속 켜짐)"""
        with self.lock:
            if self.is_session_active:
                logger.warning("⚠️ 이미 세션이 활성화되어 있습니다.")
                return False
            
            self.is_session_active = True
            self.is_processing = False
            self.audio_buffer.clear()
            self.speech_segments.clear()
            self.last_result = ""
            self.silence_frames = 0
            self.speech_frames = 0
            
            logger.info("=" * 60)
            logger.info("🎤 음성인식 세션 시작")
            logger.info("   - 마이크 활성화: 계속 듣기 모드")
            logger.info("   - 에너지 기반 VAD로 음성 자동 감지")
            logger.info("=" * 60)
            return True

    def stop_session(self):
        """음성인식 세션 종료 (마이크 끔)"""
        with self.lock:
            if not self.is_session_active:
                logger.warning("⚠️ 활성화된 세션이 없습니다.")
                return None
            
            logger.info("⏹️ 음성인식 세션 종료 요청")
            
            # 남은 버퍼가 있으면 처리
            if len(self.audio_buffer) > 0 and self.is_processing:
                speech_audio = np.array(self.audio_buffer)
                duration = len(speech_audio) / self.sample_rate
                
                if duration >= self.min_speech_duration:
                    result = self._process_speech_segment(speech_audio)
                    if result:
                        self.speech_segments.append(result)
            
            self.is_session_active = False
            self.is_processing = False
            
            # 세션 통계
            segment_count = len(self.speech_segments)
            total_duration = sum(seg.get('duration', 0) for seg in self.speech_segments)
            
            logger.info(f"📊 세션 통계:")
            logger.info(f"   - 감지된 음성 구간: {segment_count}개")
            logger.info(f"   - 총 음성 길이: {total_duration:.1f}초")
            
            result = {
                'segments': self.speech_segments.copy(),
                'total_segments': segment_count,
                'total_duration': total_duration
            }
            
            self.audio_buffer.clear()
            self.speech_segments.clear()
            self.silence_frames = 0
            self.speech_frames = 0
            
            return result

    def process_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[Dict]:
        """
        오디오 청크 처리 (asr_api_server.py에서 사용)
        
        Args:
            audio_chunk: float32 PCM 오디오 데이터 (16kHz)
        
        Returns:
            음성 감지 및 인식 결과 딕셔너리 또는 None
        """
        return self.add_audio_chunk(audio_chunk)

    def add_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[Dict]:
        """
        오디오 청크 추가 및 VAD 기반 처리
        
        Returns:
            음성 감지 및 인식 결과 딕셔너리 또는 None
        """
        with self.lock:
            if not self.is_session_active:
                return None
            
            try:
                # 음성 활동 감지
                is_speech = self._is_speech(audio_chunk)
                
                if is_speech:
                    # 음성이 감지되면
                    self.silence_frames = 0
                    self.speech_frames += 1
                    
                    if not self.is_processing:
                        # 새로운 음성 구간 시작
                        self.is_processing = True
                        self.audio_buffer.clear()
                        logger.info("🗣️ 음성 감지 시작")
                    
                    self.audio_buffer.extend(audio_chunk)
                else:
                    # 침묵이 감지되면
                    self.silence_frames += 1
                    
                    if self.is_processing:
                        # 음성 처리 중인 경우 버퍼에 추가 (짧은 침묵 포함)
                        self.audio_buffer.extend(audio_chunk)
                        
                        # 침묵 시간 계산
                        silence_duration = (self.silence_frames * len(audio_chunk)) / self.sample_rate
                        
                        # 충분한 침묵이 감지되면 음성 구간 처리
                        if silence_duration >= self.silence_duration:
                            speech_audio = np.array(self.audio_buffer)
                            duration = len(speech_audio) / self.sample_rate
                            
                            if duration >= self.min_speech_duration:
                                result = self._process_speech_segment(speech_audio)
                                
                                if result:
                                    logger.info(f"✅ 음성 처리 완료 ({duration:.1f}초)")
                                    self.speech_segments.append(result)
                                    self.is_processing = False
                                    self.audio_buffer.clear()
                                    self.silence_frames = 0
                                    self.speech_frames = 0
                                    return result
                            else:
                                logger.debug(f"⏭️ 너무 짧은 음성 무시 ({duration:.1f}초)")
                            
                            self.is_processing = False
                            self.audio_buffer.clear()
                            self.silence_frames = 0
                            self.speech_frames = 0
                
            except Exception as e:
                logger.error(f"❌ 오디오 처리 중 오류: {e}", exc_info=True)
                return None
        
        return None

    def _process_speech_segment(self, audio_data: np.ndarray) -> Optional[Dict]:
        """음성 구간 처리 및 인식"""
        try:
            duration = len(audio_data) / self.sample_rate
            
            # 음성인식 수행
            stream = self.recognizer.create_stream()
            stream.accept_waveform(self.sample_rate, audio_data)
            self.recognizer.decode_stream(stream)
            result = stream.result
            
            text = result.text.strip()
            
            if text:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                segment_result = {
                    'timestamp': timestamp,
                    'text': text,
                    'duration': duration,
                    'confidence': 1.0  # Sherpa-ONNX는 confidence score를 제공하지 않음
                }
                
                logger.info(f"📝 인식 결과: {text}")
                self.last_result = text
                
                return segment_result
            else:
                logger.debug("🔇 인식된 텍스트 없음")
                return None
        
        except Exception as e:
            logger.error(f"❌ 음성 인식 오류: {e}", exc_info=True)
            return None

    def get_session_status(self) -> Dict:
        """현재 세션 상태 반환"""
        with self.lock:
            return {
                'is_active': self.is_session_active,
                'is_processing': self.is_processing,
                'segments_count': len(self.speech_segments),
                'last_result': self.last_result
            }

    def reset(self):
        """완전 초기화"""
        with self.lock:
            logger.info("🔄 VADStreamingProcessor 초기화")
            self.is_session_active = False
            self.is_processing = False
            self.audio_buffer.clear()
            self.speech_segments.clear()
            self.last_result = ""
            self.silence_frames = 0
            self.speech_frames = 0


class StreamingProcessor:
    """Offline Recognizer를 사용한 청크 기반 스트리밍 처리 (레거시)"""

    def __init__(self, recognizer, sample_rate=16000, chunk_duration=20.0):
        self.recognizer = recognizer
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)

        self.audio_buffer = deque()
        self.is_recording = False
        self.is_ready = False
        self.accumulated_audio = []
        self.last_result = ""
        self.lock = threading.Lock()

        logger.info(f"✅ StreamingProcessor 초기화 (청크 크기: {chunk_duration}초)")
        logger.debug(f"초기 상태: is_ready={self.is_ready}, is_recording={self.is_recording}")

    def prepare(self):
        """녹음 준비 (is_recording은 False 유지)"""
        with self.lock:
            old_state = (self.is_ready, self.is_recording)

            self.is_ready = True
            self.is_recording = False
            self.audio_buffer.clear()
            self.accumulated_audio.clear()
            self.last_result = ""

            new_state = (self.is_ready, self.is_recording)

            logger.info("=" * 60)
            logger.info("🟡 녹음 준비 완료")
            logger.debug(f"상태 변경: {old_state} → {new_state}")
            logger.debug(f"버퍼 초기화 완료")
            logger.info("=" * 60)

    def start_recording(self):
        """녹음 시작 (마이크 활성화 시 호출)"""
        with self.lock:
            if not self.is_ready:
                logger.warning("⚠️ 준비되지 않은 상태에서 녹음 시작 시도")
                logger.debug(f"현재 상태: is_ready={self.is_ready}, is_recording={self.is_recording}")
                return False

            old_state = self.is_recording
            self.is_recording = True

            logger.info("=" * 60)
            logger.info("🔴 녹음 시작")
            logger.debug(f"is_recording: {old_state} → {self.is_recording}")
            logger.info("=" * 60)
            return True

    def stop_recording(self):
        """녹음 종료 및 최종 처리"""
        with self.lock:
            logger.info("⏹️ 녹음 종료 요청")
            logger.debug(f"현재 상태: is_ready={self.is_ready}, is_recording={self.is_recording}")

            if not self.is_recording:
                logger.warning("녹음 중이 아닌 상태에서 종료 요청")
                return None

            self.is_recording = False
            self.is_ready = False

            logger.debug(f"상태 변경: is_recording={True} → {False}, is_ready={True} → {False}")

            # 남은 버퍼 처리
            if len(self.accumulated_audio) > 0:
                final_audio = np.concatenate(self.accumulated_audio)
                duration = len(final_audio) / self.sample_rate
                logger.info(f"최종 오디오 처리: {duration:.2f}초")

                result = self._process_audio(final_audio)
                logger.info(f"⏹️ 녹음 종료 - 최종 길이: {duration:.2f}초")
                return result

            logger.warning("누적된 오디오가 없음")
            return self.last_result

    def add_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[str]:
        """오디오 청크 추가 및 처리"""
        with self.lock:
            # is_ready이면서 is_recording=False인 경우: 첫 오디오 도착 시 자동 시작
            if self.is_ready and not self.is_recording:
                self.is_recording = True
                logger.info("🎤 마이크 활성화 감지 → 자동 녹음 시작")
                logger.debug(f"is_recording: False → True (자동 전환)")

            if not self.is_recording:
                logger.debug(f"녹음 중이 아니므로 오디오 청크 무시 (is_ready={self.is_ready})")
                return None

            try:
                # 버퍼에 추가
                chunk_len = len(audio_chunk)
                self.audio_buffer.extend(audio_chunk)
                self.accumulated_audio.append(audio_chunk)

                logger.debug(f"오디오 청크 추가: {chunk_len} samples, 누적: {len(self.accumulated_audio)} chunks")

                # 청크 크기 충족 시 처리
                if len(self.audio_buffer) >= self.chunk_size:
                    logger.debug(f"청크 크기 도달: {len(self.audio_buffer)} >= {self.chunk_size}")

                    # 전체 누적 오디오로 처리 (더 나은 컨텍스트)
                    full_audio = np.concatenate(self.accumulated_audio)
                    result = self._process_audio(full_audio)

                    # 버퍼 일부만 유지 (overlap)
                    overlap_size = self.chunk_size // 4
                    self.audio_buffer = deque(list(self.audio_buffer)[self.chunk_size - overlap_size:])

                    logger.debug(f"버퍼 업데이트: overlap={overlap_size}, 남은 버퍼={len(self.audio_buffer)}")

                    if result and result != self.last_result:
                        self.last_result = result
                        logger.info(f"새로운 인식 결과: {result[:50]}...")
                        return result

            except Exception as e:
                logger.error(f"❌ 오디오 청크 처리 중 오류: {e}", exc_info=True)
                return None

        return None

    def _process_audio(self, audio_data: np.ndarray) -> str:
        """오디오 데이터 처리"""
        try:
            duration = len(audio_data) / self.sample_rate
            logger.debug(f"음성인식 처리 시작: {duration:.2f}초")

            if duration < 0.5:
                logger.debug("오디오 길이가 0.5초 미만, 처리 건너뜀")
                return ""

            # Offline Recognizer로 처리
            stream = self.recognizer.create_stream()
            stream.accept_waveform(self.sample_rate, audio_data)
            self.recognizer.decode_stream(stream)
            result = stream.result

            text = result.text.strip()
            logger.debug(f"음성인식 결과: '{text}'")
            return text

        except Exception as e:
            logger.error(f"❌ 오디오 처리 오류: {e}", exc_info=True)
            return ""

    def get_current_duration(self) -> float:
        """현재 녹음 길이 반환"""
        if len(self.accumulated_audio) > 0:
            total_samples = sum(len(chunk) for chunk in self.accumulated_audio)
            duration = total_samples / self.sample_rate
            logger.debug(f"현재 녹음 길이: {duration:.2f}초 ({len(self.accumulated_audio)} chunks)")
            return duration
        return 0.0

    def reset(self):
        """완전 초기화"""
        with self.lock:
            logger.info("🔄 StreamingProcessor 완전 초기화")
            logger.debug(f"초기화 전 상태: is_ready={self.is_ready}, is_recording={self.is_recording}")

            self.is_recording = False
            self.is_ready = False
            self.audio_buffer.clear()
            self.accumulated_audio.clear()
            self.last_result = ""

            logger.debug("초기화 완료: is_ready=False, is_recording=False, 버퍼 비움")

