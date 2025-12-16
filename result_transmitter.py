# -*- coding: utf-8 -*-
"""
ASR 결과 전송 모듈

재시도 로직, 큐잉 시스템, 메트릭 수집을 포함한 결과 전송 기능
"""

import os
import asyncio
import logging
import time
import threading
from typing import Dict, Optional, List
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

import httpx
from .exceptions import EmergencyAlertError

logger = logging.getLogger(__name__)


class TransmissionStatus(Enum):
    """전송 상태"""
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ResultMessage:
    """전송할 결과 메시지"""
    device_id: int
    device_name: str
    session_id: str
    text: str
    timestamp: str
    duration: float
    is_emergency: bool
    emergency_keywords: List[str]
    status: TransmissionStatus = TransmissionStatus.PENDING
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None


@dataclass
class TransmissionMetrics:
    """전송 메트릭"""
    total_sent: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_retries: int = 0
    average_latency: float = 0.0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_sent == 0:
            return 0.0
        return (self.total_success / self.total_sent) * 100.0


class ResultTransmitter:
    """ASR 결과 전송 클래스 (재시도, 큐잉, 메트릭 포함)"""
    
    def __init__(
        self,
        backend_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_queue_size: int = 1000,
        batch_size: int = 10,
        timeout: float = 10.0,
    ):
        """
        Args:
            backend_url: 백엔드 API URL
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 지연 시간 (초)
            max_queue_size: 최대 큐 크기
            batch_size: 배치 처리 크기
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.backend_url = backend_url or os.getenv(
            "BACKEND_URL", "http://localhost:8000"
        )
        self.endpoint = f"{self.backend_url}/asr/result"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.timeout = timeout
        
        # 큐 및 메트릭
        self.queue: deque = deque(maxlen=max_queue_size)
        self.metrics = TransmissionMetrics()
        self.lock = threading.Lock()
        
        # HTTP 클라이언트
        self.client = httpx.AsyncClient(timeout=timeout)
        
        # 백그라운드 작업
        self._worker_running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        logger.info(f"✅ ResultTransmitter 초기화: endpoint={self.endpoint}")
    
    def start_worker(self):
        """백그라운드 워커 시작"""
        if self._worker_running:
            return
        
        self._worker_running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="ResultTransmitterWorker"
        )
        self._worker_thread.start()
        logger.info("✅ ResultTransmitter 워커 시작")
    
    def stop_worker(self):
        """백그라운드 워커 중지"""
        self._worker_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        logger.info("🛑 ResultTransmitter 워커 중지")
    
    def _worker_loop(self):
        """백그라운드 워커 루프"""
        while self._worker_running:
            try:
                # 큐에서 메시지 처리
                messages_to_send = []
                
                with self.lock:
                    # 큐에서 배치 크기만큼 가져오기
                    for _ in range(min(self.batch_size, len(self.queue))):
                        if self.queue:
                            msg = self.queue.popleft()
                            messages_to_send.append(msg)
                
                # 메시지 전송
                for msg in messages_to_send:
                    asyncio.run(self._send_message(msg))
                
                # 큐가 비어있으면 잠시 대기
                if not messages_to_send:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"❌ 워커 루프 오류: {e}", exc_info=True)
                time.sleep(1.0)
    
    async def _send_message(self, message: ResultMessage) -> bool:
        """
        메시지 전송 (재시도 로직 포함)
        
        Returns:
            전송 성공 여부
        """
        message.status = TransmissionStatus.SENDING
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                # HTTP POST 요청
                payload = {
                    "device_id": message.device_id,
                    "device_name": message.device_name,
                    "session_id": message.session_id,
                    "text": message.text,
                    "timestamp": message.timestamp,
                    "duration": message.duration,
                    "is_emergency": message.is_emergency,
                    "emergency_keywords": message.emergency_keywords,
                }
                
                response = await self.client.post(
                    self.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                latency = time.time() - start_time
                
                # 성공
                if response.status_code == 200:
                    message.status = TransmissionStatus.SUCCESS
                    
                    with self.lock:
                        self.metrics.total_sent += 1
                        self.metrics.total_success += 1
                        self.metrics.last_success_time = time.time()
                        # 평균 지연 시간 업데이트
                        if self.metrics.average_latency == 0:
                            self.metrics.average_latency = latency
                        else:
                            self.metrics.average_latency = (
                                self.metrics.average_latency * 0.9 + latency * 0.1
                            )
                    
                    logger.info(
                        f"✅ 결과 전송 성공: device_id={message.device_id}, "
                        f"text='{message.text[:30]}...', latency={latency:.3f}s"
                    )
                    return True
                
                # 실패 (재시도 가능)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    message.last_error = error_msg
                    
                    if attempt < self.max_retries:
                        message.status = TransmissionStatus.RETRYING
                        message.retry_count += 1
                        
                        with self.lock:
                            self.metrics.total_retries += 1
                        
                        wait_time = self.retry_delay * (2 ** attempt)  # 지수 백오프
                        logger.warning(
                            f"⚠️ 전송 실패 (재시도 {attempt + 1}/{self.max_retries}): "
                            f"{error_msg}, {wait_time:.1f}초 후 재시도"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # 최대 재시도 횟수 초과
                        message.status = TransmissionStatus.FAILED
                        
                        with self.lock:
                            self.metrics.total_sent += 1
                            self.metrics.total_failed += 1
                            self.metrics.last_failure_time = time.time()
                        
                        logger.error(
                            f"❌ 결과 전송 실패 (최대 재시도 초과): "
                            f"device_id={message.device_id}, error={error_msg}"
                        )
                        return False
            
            except httpx.TimeoutException:
                error_msg = "요청 타임아웃"
                message.last_error = error_msg
                
                if attempt < self.max_retries:
                    message.status = TransmissionStatus.RETRYING
                    message.retry_count += 1
                    
                    with self.lock:
                        self.metrics.total_retries += 1
                    
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ 타임아웃 (재시도 {attempt + 1}/{self.max_retries}): "
                        f"{wait_time:.1f}초 후 재시도"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    message.status = TransmissionStatus.FAILED
                    
                    with self.lock:
                        self.metrics.total_sent += 1
                        self.metrics.total_failed += 1
                        self.metrics.last_failure_time = time.time()
                    
                    logger.error(
                        f"❌ 결과 전송 실패 (타임아웃): device_id={message.device_id}"
                    )
                    return False
            
            except Exception as e:
                error_msg = str(e)
                message.last_error = error_msg
                
                if attempt < self.max_retries:
                    message.status = TransmissionStatus.RETRYING
                    message.retry_count += 1
                    
                    with self.lock:
                        self.metrics.total_retries += 1
                    
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ 전송 오류 (재시도 {attempt + 1}/{self.max_retries}): "
                        f"{error_msg}, {wait_time:.1f}초 후 재시도"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    message.status = TransmissionStatus.FAILED
                    
                    with self.lock:
                        self.metrics.total_sent += 1
                        self.metrics.total_failed += 1
                        self.metrics.last_failure_time = time.time()
                    
                    logger.error(
                        f"❌ 결과 전송 실패: device_id={message.device_id}, error={error_msg}",
                        exc_info=True
                    )
                    return False
        
        return False
    
    def enqueue(
        self,
        device_id: int,
        device_name: str,
        session_id: str,
        text: str,
        timestamp: str,
        duration: float,
        is_emergency: bool = False,
        emergency_keywords: Optional[List[str]] = None,
    ) -> bool:
        """
        결과 메시지를 큐에 추가
        
        Returns:
            큐 추가 성공 여부 (큐가 가득 찬 경우 False)
        """
        message = ResultMessage(
            device_id=device_id,
            device_name=device_name,
            session_id=session_id,
            text=text,
            timestamp=timestamp,
            duration=duration,
            is_emergency=is_emergency,
            emergency_keywords=emergency_keywords or [],
        )
        
        with self.lock:
            if len(self.queue) >= self.max_queue_size:
                logger.warning(
                    f"⚠️ 큐가 가득 참 (크기: {len(self.queue)}/{self.max_queue_size}). "
                    f"메시지 드롭: device_id={device_id}"
                )
                return False
            
            self.queue.append(message)
            logger.debug(
                f"📥 큐에 추가: device_id={device_id}, "
                f"큐 크기: {len(self.queue)}/{self.max_queue_size}"
            )
        
        return True
    
    def get_metrics(self) -> Dict:
        """메트릭 조회"""
        with self.lock:
            return {
                "total_sent": self.metrics.total_sent,
                "total_success": self.metrics.total_success,
                "total_failed": self.metrics.total_failed,
                "total_retries": self.metrics.total_retries,
                "success_rate": self.metrics.success_rate(),
                "average_latency": self.metrics.average_latency,
                "queue_size": len(self.queue),
                "last_success_time": (
                    datetime.fromtimestamp(self.metrics.last_success_time).isoformat()
                    if self.metrics.last_success_time
                    else None
                ),
                "last_failure_time": (
                    datetime.fromtimestamp(self.metrics.last_failure_time).isoformat()
                    if self.metrics.last_failure_time
                    else None
                ),
            }
    
    def reset_metrics(self):
        """메트릭 초기화"""
        with self.lock:
            self.metrics = TransmissionMetrics()
        logger.info("🔄 메트릭 초기화 완료")
    
    async def close(self):
        """리소스 정리"""
        self.stop_worker()
        await self.client.aclose()
        logger.info("✅ ResultTransmitter 리소스 정리 완료")


# 전역 인스턴스
_transmitter: Optional[ResultTransmitter] = None


def get_transmitter() -> ResultTransmitter:
    """전역 전송기 인스턴스 가져오기"""
    global _transmitter
    
    if _transmitter is None:
        _transmitter = ResultTransmitter()
        _transmitter.start_worker()
    
    return _transmitter


async def send_result_to_backend(
    device_id: int,
    device_name: str,
    session_id: str,
    text: str,
    timestamp: str,
    duration: float,
    is_emergency: bool = False,
    emergency_keywords: Optional[List[str]] = None,
) -> bool:
    """
    백엔드로 결과 전송 (비동기, 큐잉)
    
    Returns:
        큐 추가 성공 여부
    """
    transmitter = get_transmitter()
    return transmitter.enqueue(
        device_id=device_id,
        device_name=device_name,
        session_id=session_id,
        text=text,
        timestamp=timestamp,
        duration=duration,
        is_emergency=is_emergency,
        emergency_keywords=emergency_keywords,
    )

