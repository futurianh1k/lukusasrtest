# -*- coding: utf-8 -*-
"""
유틸리티 모듈

오디오 처리, 파일 읽기 등 유틸리티 함수
"""

import logging
import wave
import numpy as np

logger = logging.getLogger(__name__)


def resample_audio(audio_data, orig_sr, target_sr=16000):
    """
    오디오 리샘플링
    
    Args:
        audio_data: 오디오 데이터 (numpy array)
        orig_sr: 원본 샘플레이트
        target_sr: 목표 샘플레이트 (기본값: 16000)
    
    Returns:
        리샘플링된 오디오 데이터
    """
    if orig_sr == target_sr:
        return audio_data

    try:
        import librosa
        return librosa.resample(audio_data, orig_sr=orig_sr, target_sr=target_sr)
    except ImportError:
        try:
            from scipy import signal
            num_samples = int(len(audio_data) * target_sr / orig_sr)
            return signal.resample(audio_data, num_samples)
        except ImportError:
            logger.error("❌ librosa 또는 scipy가 설치되어 있지 않습니다.")
            raise ImportError(
                "오디오 리샘플링을 위해 librosa 또는 scipy가 필요합니다.\n"
                "다음 명령어로 설치하세요:\n"
                "pip install librosa\n"
                "또는\n"
                "pip install scipy"
            )


def read_wave(wave_filename: str):
    """
    Wave 파일 읽기
    
    Args:
        wave_filename: Wave 파일 경로
    
    Returns:
        (samples_float32, sample_rate) 튜플
    
    Raises:
        ValueError: 모노 또는 16비트가 아닌 경우
    """
    with wave.open(wave_filename) as f:
        if f.getnchannels() != 1:
            raise ValueError(f"모노 오디오만 지원. 채널: {f.getnchannels()}")
        if f.getsampwidth() != 2:
            raise ValueError(f"16비트 오디오만 지원. 샘플폭: {f.getsampwidth()}")

        num_samples = f.getnframes()
        samples = f.readframes(num_samples)
        samples_int16 = np.frombuffer(samples, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768.0
        return samples_float32, f.getframerate()

