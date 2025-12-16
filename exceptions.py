# -*- coding: utf-8 -*-
"""
커스텀 예외 클래스 모듈

ASR 서버 전용 예외 클래스 정의
"""


class ASRError(Exception):
    """ASR 서버 기본 예외 클래스"""
    pass


class ModelLoadError(ASRError):
    """모델 로딩 실패 예외"""
    pass


class AudioProcessingError(ASRError):
    """오디오 처리 오류 예외"""
    pass


class RecognitionError(ASRError):
    """음성인식 오류 예외"""
    pass


class SessionError(ASRError):
    """세션 관리 오류 예외"""
    pass


class EmergencyAlertError(ASRError):
    """응급 알림 전송 오류 예외"""
    pass


class ReportGenerationError(ASRError):
    """리포트 생성 오류 예외"""
    pass

