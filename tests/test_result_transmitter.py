# -*- coding: utf-8 -*-
"""
결과 전송 모듈 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from rk3588asr.result_transmitter import (
    ResultTransmitter,
    ResultMessage,
    TransmissionStatus,
)


@pytest.fixture
def transmitter():
    """테스트용 transmitter 인스턴스"""
    return ResultTransmitter(
        backend_url="http://localhost:8000",
        max_retries=2,
        retry_delay=0.1,
        max_queue_size=10,
        timeout=5.0,
    )


def test_enqueue(transmitter):
    """큐에 메시지 추가 테스트"""
    success = transmitter.enqueue(
        device_id=1,
        device_name="TestDevice",
        session_id="test-session",
        text="테스트 텍스트",
        timestamp="2025-12-10 10:00:00",
        duration=1.0,
    )
    assert success is True
    assert len(transmitter.queue) == 1


def test_enqueue_full_queue(transmitter):
    """큐가 가득 찬 경우 테스트"""
    # 큐 채우기
    for i in range(transmitter.max_queue_size):
        transmitter.enqueue(
            device_id=1,
            device_name="TestDevice",
            session_id=f"session-{i}",
            text=f"text-{i}",
            timestamp="2025-12-10 10:00:00",
            duration=1.0,
        )
    
    # 큐가 가득 찬 상태에서 추가 시도
    success = transmitter.enqueue(
        device_id=1,
        device_name="TestDevice",
        session_id="overflow-session",
        text="overflow",
        timestamp="2025-12-10 10:00:00",
        duration=1.0,
    )
    assert success is False


@pytest.mark.asyncio
async def test_send_message_success(transmitter):
    """전송 성공 테스트"""
    message = ResultMessage(
        device_id=1,
        device_name="TestDevice",
        session_id="test-session",
        text="테스트",
        timestamp="2025-12-10 10:00:00",
        duration=1.0,
    )
    
    with patch.object(transmitter.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = await transmitter._send_message(message)
        
        assert success is True
        assert message.status == TransmissionStatus.SUCCESS
        assert transmitter.metrics.total_success == 1


@pytest.mark.asyncio
async def test_send_message_retry(transmitter):
    """재시도 테스트"""
    message = ResultMessage(
        device_id=1,
        device_name="TestDevice",
        session_id="test-session",
        text="테스트",
        timestamp="2025-12-10 10:00:00",
        duration=1.0,
    )
    
    with patch.object(transmitter.client, 'post', new_callable=AsyncMock) as mock_post:
        # 첫 번째 시도: 실패, 두 번째 시도: 성공
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]
        
        success = await transmitter._send_message(message)
        
        assert success is True
        assert message.retry_count == 1
        assert transmitter.metrics.total_retries == 1


def test_metrics(transmitter):
    """메트릭 테스트"""
    metrics = transmitter.get_metrics()
    
    assert "total_sent" in metrics
    assert "total_success" in metrics
    assert "total_failed" in metrics
    assert "success_rate" in metrics
    assert "queue_size" in metrics


def test_reset_metrics(transmitter):
    """메트릭 초기화 테스트"""
    transmitter.metrics.total_sent = 10
    transmitter.reset_metrics()
    
    assert transmitter.metrics.total_sent == 0
    assert transmitter.metrics.total_success == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

