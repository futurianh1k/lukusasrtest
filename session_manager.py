# -*- coding: utf-8 -*-
"""
세션 관리 모듈

마이크 실시간 음성인식 세션 결과 관리
"""

import logging
import threading
from typing import List, Dict
from collections import deque

logger = logging.getLogger(__name__)


class MicrophoneSessionRecorder:
    """마이크 실시간 음성인식 세션 결과를 누적 저장하는 클래스"""

    def __init__(self):
        self.sessions = []  # 각 세션의 결과를 저장
        self.current_session_id = 0
        self.lock = threading.Lock()

    def add_session_result(self, ground_truth: str, asr_result: str, duration: float, timestamp: str):
        """세션 결과 추가"""
        with self.lock:
            self.current_session_id += 1
            session_data = {
                "session_id": self.current_session_id,
                "timestamp": timestamp,
                "duration": duration,
                "ground_truth": ground_truth,
                "asr_result": asr_result,
            }
            self.sessions.append(session_data)
            logger.info(f"✅ 세션 결과 저장 완료: Session #{self.current_session_id}")

    def get_all_sessions(self) -> List[Dict]:
        """모든 세션 결과 반환"""
        with self.lock:
            return self.sessions.copy()

    def get_session_count(self) -> int:
        """저장된 세션 개수 반환"""
        with self.lock:
            return len(self.sessions)

    def clear_sessions(self):
        """모든 세션 결과 초기화"""
        with self.lock:
            self.sessions.clear()
            self.current_session_id = 0
            logger.info("🔄 세션 결과 초기화 완료")


# 전역 세션 레코더
mic_session_recorder = MicrophoneSessionRecorder()


# VAD 세션 채팅 히스토리 (실시간 누적 표시용)
vad_chat_history = []


def clear_vad_chat_history():
    """VAD 채팅 히스토리 초기화"""
    global vad_chat_history
    vad_chat_history = []
    logger.info("🗑️ VAD 채팅 히스토리 초기화")


def add_to_vad_chat_history(timestamp: str, text: str, duration: float, is_emergency: bool = False, emergency_keywords: list = None):
    """VAD 채팅 히스토리에 메시지 추가"""
    global vad_chat_history
    
    message = {
        'timestamp': timestamp,
        'text': text,
        'duration': duration,
        'is_emergency': is_emergency,
        'emergency_keywords': emergency_keywords or []
    }
    
    vad_chat_history.append(message)
    logger.debug(f"📝 채팅 히스토리 추가: {len(vad_chat_history)}개")


def format_vad_chat_history() -> str:
    """VAD 채팅 히스토리를 포맷팅하여 문자열로 반환"""
    global vad_chat_history
    
    if not vad_chat_history:
        return "👂 대기 중... 말씀해주세요."
    
    formatted = "🔴 음성인식 세션 활성화 중...\n\n"
    formatted += f"📊 감지된 음성 구간: {len(vad_chat_history)}개\n\n"
    formatted += "=" * 60 + "\n\n"
    
    for idx, msg in enumerate(vad_chat_history, 1):
        timestamp = msg['timestamp']
        text = msg['text']
        duration = msg['duration']
        is_emergency = msg['is_emergency']
        emergency_keywords = msg['emergency_keywords']
        
        # 구간 번호와 시간 표시
        formatted += f"[{idx}] {timestamp} ({duration:.1f}초)\n"
        
        # 응급 상황 표시
        if is_emergency:
            formatted += f"🚨 응급: {text}\n"
            formatted += f"   키워드: {', '.join(emergency_keywords)}\n"
        else:
            formatted += f"💬 {text}\n"
        
        formatted += "\n"
    
    formatted += "=" * 60 + "\n"
    formatted += "👂 계속 듣고 있습니다. 말씀해주세요..."
    
    return formatted

