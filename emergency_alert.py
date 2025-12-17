# -*- coding: utf-8 -*-
"""
응급 상황 알림 모듈

응급 상황 감지 시 외부 API로 알림을 전송하는 기능
"""

import logging
import uuid
import urllib.parse
import os
from datetime import datetime
from typing import List
import requests

# config import (absolute first, then relative)
try:
    from config import EMERGENCY_API_CONFIG
except Exception:
    from .config import EMERGENCY_API_CONFIG

logger = logging.getLogger(__name__)


def send_emergency_alert(recognized_text: str, emergency_keywords: List[str]):
    """
    응급 상황 감지 시 API로 이벤트 전송
    
    Args:
        recognized_text: 음성 인식 결과 텍스트
        emergency_keywords: 감지된 응급 키워드 리스트
    """
    if not EMERGENCY_API_CONFIG.get("enabled", False):
        logger.info("⚠️ 응급 API 호출이 비활성화되어 있습니다.")
        return
    
    config = EMERGENCY_API_CONFIG
    enabled_endpoints = [ep for ep in config.get("api_endpoints", []) if ep.get("enabled", False)]
    
    if not enabled_endpoints:
        logger.warning("⚠️ 활성화된 API 엔드포인트가 없습니다.")
        return
    
    # JSON 타입 API 우선 선택
    selected_api = None
    for ep in enabled_endpoints:
        if ep.get("type") == "json":
            selected_api = ep
            break
    
    if not selected_api and enabled_endpoints:
        selected_api = enabled_endpoints[0]
    
    if not selected_api:
        logger.warning("⚠️ 사용 가능한 API 엔드포인트가 없습니다.")
        return
    
    try:
        logger.info(f"🚨 응급 상황 감지! API 호출 시작: {selected_api['name']}")
        logger.info(f"   - 인식 텍스트: {recognized_text}")
        logger.info(f"   - 감지 키워드: {', '.join(emergency_keywords)}")
        
        # 이벤트 데이터 생성
        event_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        watch_id = config.get("watch_id", "watch_default")
        sender_id = config.get("sender_id", "voice_asr_system")
        
        if selected_api.get("type") == "json":
            # JSON 방식
            api_url = selected_api['url']
            if '{watchId}' in api_url:
                api_url = api_url.replace('{watchId}', watch_id)
            elif watch_id not in api_url:
                if not api_url.endswith('/'):
                    api_url += '/'
                api_url += watch_id
            
            # 이미지 URL 생성 (선택적)
            image_url = None
            if config.get("include_image_url", False):
                image_base = config.get("image_base_url", os.getenv("IMAGE_BASE_URL", "http://localhost:8080/api/images"))
                image_filename = f"emergency_{event_id.split('-')[0]}.jpeg"
                image_url = f"{image_base}/{image_filename}"
            
            # 서버가 기대하는 형식으로만 데이터 구성
            request_data = {
                "senderId": sender_id,
                "note": f"응급 상황 감지: {recognized_text} (키워드: {', '.join(emergency_keywords)})",
                "imageUrl": image_url  # null 가능
            }
            
            logger.info(f"📤 API 요청 URL: {api_url}")
            logger.info(f"📤 요청 데이터: {request_data}")

            response = requests.post(
                url=api_url,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            logger.info(f"✅ API 호출 성공 (Status: {response.status_code})")
            logger.info(f"   - Event ID: {event_id}")
            logger.info(f"   - Response: {response.text[:200]}")
        
        else:
            # Multipart 방식
            api_url = selected_api['url']
            if '{watchId}' in api_url:
                api_url = api_url.replace('{watchId}', watch_id)
            elif watch_id not in api_url:
                if not api_url.endswith('/'):
                    api_url += '/'
                api_url += watch_id
            
            # 쿼리 파라미터로 senderId와 note 추가
            note_text = f"응급 상황 감지: {recognized_text} (키워드: {', '.join(emergency_keywords)})"
            query_params = {
                'senderId': sender_id,
                'note': note_text
            }
            api_url_with_params = f"{api_url}?{urllib.parse.urlencode(query_params)}"
            
            # multipart/form-data 형식으로 전송 (image는 빈 값)
            files = {
                'image': ('', '')  # 빈 이미지 파일
            }
            
            logger.info(f"📤 API 요청 URL: {api_url_with_params}")
            logger.info(f"📤 Multipart files: {files}")

            response = requests.post(
                url=api_url_with_params,
                files=files,
                timeout=10
            )
            
            logger.info(f"✅ API 호출 성공 (Status: {response.status_code})")
            logger.info(f"   - Response: {response.text[:200]}")
    
    except requests.exceptions.Timeout:
        logger.error("❌ API 호출 타임아웃")
    
    except requests.exceptions.ConnectionError:
        logger.error("❌ API 연결 오류")
    
    except Exception as e:
        logger.error(f"❌ API 호출 중 오류 발생: {e}", exc_info=True)

