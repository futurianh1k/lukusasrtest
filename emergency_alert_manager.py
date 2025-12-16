"""
응급 알림 관리자

주요 기능:
- API 엔드포인트 DB 관리
- 응급 상황 이벤트 전송
- 전송 결과 로깅
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from api_endpoint_db import ApiEndpointDB
from api_utils import send_to_multiple_endpoints

logger = logging.getLogger(__name__)


class EmergencyAlertManager:
    """응급 알림 관리자"""
    
    def __init__(self, db_path: str = "./data/api_endpoints.db"):
        """
        Args:
            db_path: API 엔드포인트 DB 경로
        """
        self.db = ApiEndpointDB(db_path)
        self.db.init()
        
        # 기본 설정 확인 및 초기화
        self._init_default_settings()
        
        logger.info(f"✅ EmergencyAlertManager 초기화 완료 (DB: {db_path})")
    
    def _init_default_settings(self):
        """기본 설정 초기화"""
        # watch_id 기본값 설정 (없으면)
        if not self.db.get_kv("watch_id"):
            self.db.set_kv("watch_id", "watch_default_001")
            logger.info("기본 watch_id 설정: watch_default_001")
        
        # sender_id 기본값 설정
        if not self.db.get_kv("sender_id"):
            self.db.set_kv("sender_id", "voice_asr_system")
            logger.info("기본 sender_id 설정: voice_asr_system")
    
    # ==================
    # 설정 관리
    # ==================
    def get_watch_id(self) -> str:
        """현재 watch_id 가져오기"""
        return self.db.get_kv("watch_id") or "watch_default_001"
    
    def set_watch_id(self, watch_id: str):
        """watch_id 설정"""
        self.db.set_kv("watch_id", watch_id)
        logger.info(f"watch_id 설정: {watch_id}")
    
    def get_sender_id(self) -> str:
        """현재 sender_id 가져오기"""
        return self.db.get_kv("sender_id") or "voice_asr_system"
    
    def set_sender_id(self, sender_id: str):
        """sender_id 설정"""
        self.db.set_kv("sender_id", sender_id)
        logger.info(f"sender_id 설정: {sender_id}")
    
    # ==================
    # 엔드포인트 관리
    # ==================
    def list_endpoints(self) -> List[Dict[str, Any]]:
        """모든 엔드포인트 목록 가져오기"""
        return self.db.list_endpoints()
    
    def add_endpoint(
        self, 
        name: str, 
        url: str, 
        method: str = "POST",
        endpoint_type: str = "json",
        enabled: bool = True
    ) -> int:
        """
        엔드포인트 추가
        
        Args:
            name: 엔드포인트 이름
            url: API URL
            method: HTTP 메서드 (POST, GET 등)
            endpoint_type: 전송 타입 (json 또는 multipart)
            enabled: 활성화 여부
            
        Returns:
            int: 추가된 엔드포인트 ID
        """
        endpoint_id = self.db.insert_endpoint(
            name=name,
            url=url,
            method=method,
            endpoint_type=endpoint_type,
            enabled=enabled
        )
        logger.info(f"✅ 엔드포인트 추가: {name} (ID: {endpoint_id})")
        return endpoint_id
    
    def update_endpoint(
        self,
        endpoint_id: int,
        **kwargs
    ):
        """
        엔드포인트 수정
        
        Args:
            endpoint_id: 엔드포인트 ID
            **kwargs: 수정할 필드 (name, url, method, endpoint_type, enabled)
        """
        self.db.update_endpoint(endpoint_id, **kwargs)
        logger.info(f"✅ 엔드포인트 수정: ID {endpoint_id}")
    
    def delete_endpoint(self, endpoint_id: int):
        """
        엔드포인트 삭제
        
        Args:
            endpoint_id: 엔드포인트 ID
        """
        self.db.delete_endpoint(endpoint_id)
        logger.info(f"✅ 엔드포인트 삭제: ID {endpoint_id}")
    
    def get_enabled_endpoints(self) -> List[Dict[str, Any]]:
        """활성화된 엔드포인트만 가져오기"""
        return self.db.get_enabled_endpoints()
    
    # ==================
    # 응급 알림 전송
    # ==================
    def send_emergency_alert(
        self,
        recognized_text: str,
        emergency_keywords: List[str],
        image_path: Optional[str] = None,
        timeout: int = 10,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """
        응급 상황 알림 전송
        
        Args:
            recognized_text: 인식된 텍스트
            emergency_keywords: 감지된 응급 키워드 목록
            image_path: 첨부할 이미지 경로 (선택적)
            timeout: 요청 타임아웃 (초)
            retry_count: 재시도 횟수
            
        Returns:
            dict: 전송 결과
                {
                    "success": bool,
                    "total_endpoints": int,
                    "success_count": int,
                    "failed_count": int,
                    "results": List[Dict],
                    "timestamp": str
                }
        """
        # 활성화된 엔드포인트 가져오기
        endpoints = self.get_enabled_endpoints()
        
        if not endpoints:
            logger.warning("⚠️ 활성화된 API 엔드포인트가 없습니다.")
            return {
                "success": False,
                "total_endpoints": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "timestamp": datetime.now().isoformat(),
                "error": "No active endpoints"
            }
        
        # 이벤트 데이터 생성
        event_id = str(uuid.uuid4())
        watch_id = self.get_watch_id()
        sender_id = self.get_sender_id()
        
        event_data = {
            "eventId": event_id,
            "watchId": watch_id,
            "senderId": sender_id,
            "eventType": "emergency_voice",
            "note": "응급 호출 발생",
            "recognizedText": recognized_text,
            "emergencyKeywords": emergency_keywords,
            "timestamp": datetime.now().isoformat(),
            "status": 1,  # 1: 발생, 0: 해제
        }
        
        logger.warning(f"🚨 응급 알림 전송 시작")
        logger.warning(f"   이벤트 ID: {event_id}")
        logger.warning(f"   인식 텍스트: {recognized_text}")
        logger.warning(f"   응급 키워드: {', '.join(emergency_keywords)}")
        logger.warning(f"   대상 엔드포인트: {len(endpoints)}개")
        
        # 다중 엔드포인트 전송 (비동기)
        results = send_to_multiple_endpoints(
            endpoints=endpoints,
            event_data=event_data,
            image_path=image_path,
            timeout=timeout,
            retry_count=retry_count,
            async_mode=True,
        )
        
        # 결과 집계
        success_count = sum(1 for r in results if r["result"].get("success"))
        failed_count = len(results) - success_count
        
        summary = {
            "success": success_count > 0,
            "total_endpoints": len(endpoints),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "event_id": event_id,
        }
        
        if success_count > 0:
            logger.info(f"✅ 응급 알림 전송 성공: {success_count}/{len(endpoints)}개 엔드포인트")
        else:
            logger.error(f"❌ 응급 알림 전송 실패: 모든 엔드포인트 전송 실패")
        
        return summary
    
    def test_endpoint(
        self,
        endpoint_id: int,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        특정 엔드포인트 테스트
        
        Args:
            endpoint_id: 엔드포인트 ID
            timeout: 타임아웃 (초)
            
        Returns:
            dict: 테스트 결과
        """
        from api_utils import send_api_event
        
        # 엔드포인트 정보 가져오기
        endpoints = self.list_endpoints()
        endpoint = next((ep for ep in endpoints if ep["id"] == endpoint_id), None)
        
        if not endpoint:
            return {
                "success": False,
                "error": f"Endpoint ID {endpoint_id} not found"
            }
        
        # 테스트 데이터
        test_data = {
            "eventId": str(uuid.uuid4()),
            "watchId": self.get_watch_id(),
            "senderId": self.get_sender_id(),
            "eventType": "test",
            "note": "API 연결 테스트",
            "recognizedText": "테스트 메시지",
            "timestamp": datetime.now().isoformat(),
            "status": 1,
        }
        
        logger.info(f"🧪 엔드포인트 테스트: {endpoint['name']} ({endpoint['url']})")
        
        # 전송
        result = send_api_event(
            url=endpoint["url"],
            event_data=test_data,
            timeout=timeout,
            retry_count=1,
        )
        
        if result.get("success"):
            logger.info(f"✅ 테스트 성공: {endpoint['name']}")
        else:
            logger.error(f"❌ 테스트 실패: {endpoint['name']} - {result.get('error')}")
        
        return result


# 전역 인스턴스 (싱글톤)
_manager_instance: Optional[EmergencyAlertManager] = None


def get_emergency_manager() -> EmergencyAlertManager:
    """전역 EmergencyAlertManager 인스턴스 가져오기 (싱글톤)"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = EmergencyAlertManager()
    return _manager_instance


def send_emergency_alert(
    recognized_text: str,
    emergency_keywords: List[str],
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    응급 알림 전송 (편의 함수)
    
    Args:
        recognized_text: 인식된 텍스트
        emergency_keywords: 응급 키워드 목록
        image_path: 이미지 경로 (선택적)
        
    Returns:
        dict: 전송 결과
    """
    manager = get_emergency_manager()
    return manager.send_emergency_alert(
        recognized_text=recognized_text,
        emergency_keywords=emergency_keywords,
        image_path=image_path,
    )
