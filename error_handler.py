# -*- coding: utf-8 -*-
"""
에러 처리 모듈

커스텀 예외 핸들러 및 에러 처리 유틸리티
"""

import os
import logging
import traceback
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    ASRError,
    ModelLoadError,
    AudioProcessingError,
    RecognitionError,
    SessionError,
    EmergencyAlertError,
    ReportGenerationError,
)

logger = logging.getLogger(__name__)

# 프로덕션 환경 여부
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"


def create_error_response(
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    include_details: bool = False,
) -> JSONResponse:
    """
    에러 응답 생성
    
    Args:
        error: 예외 객체
        status_code: HTTP 상태 코드
        include_details: 상세 정보 포함 여부 (프로덕션에서는 False)
    
    Returns:
        JSONResponse: 에러 응답
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    # 프로덕션 환경에서는 상세 정보 숨김
    if IS_PRODUCTION and not include_details:
        user_message = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        details = None
    else:
        user_message = error_message
        details = {
            "error_type": error_type,
            "traceback": traceback.format_exc() if include_details else None,
        }
    
    # 내부 로그에는 항상 상세 정보 기록
    logger.error(
        f"❌ 에러 발생: {error_type} - {error_message}",
        exc_info=True
    )
    
    response_data: Dict[str, Any] = {
        "status": "error",
        "message": user_message,
    }
    
    if details:
        response_data["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def asr_exception_handler(request: Request, exc: ASRError) -> JSONResponse:
    """ASR 예외 핸들러"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # 예외 타입에 따른 상태 코드 설정
    if isinstance(exc, ModelLoadError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, SessionError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, AudioProcessingError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, RecognitionError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(exc, EmergencyAlertError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, ReportGenerationError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return create_error_response(exc, status_code, include_details=not IS_PRODUCTION)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 핸들러"""
    return create_error_response(exc, include_details=not IS_PRODUCTION)


def safe_execute(func, *args, **kwargs):
    """
    안전한 함수 실행 (예외 처리 포함)
    
    Args:
        func: 실행할 함수
        *args: 함수 인자
        **kwargs: 함수 키워드 인자
    
    Returns:
        (success: bool, result: Any, error: Exception)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        logger.error(f"❌ 함수 실행 실패: {func.__name__} - {e}", exc_info=True)
        return False, None, e

