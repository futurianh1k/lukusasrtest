"""
통합 API 전송 유틸리티

주요 기능:
- 재시도 로직 (exponential backoff)
- 비동기 전송 (ThreadPoolExecutor)
- Multipart/JSON 자동 선택
- 안전한 예외 처리
- 선택적 로깅 (실패해도 에러 나지 않음)
"""

import uuid
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 비동기 전송용 스레드 풀 (전역)
_executor: Optional[ThreadPoolExecutor] = None
_executor_max_workers = 4


def _safe_log(level: str, message: str):
    """
    안전한 로깅 - 로깅 실패 시에도 프로그램이 중단되지 않음

    Args:
        level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG)
        message: 로그 메시지
    """
    try:
        import logging
        logger = logging.getLogger(__name__)

        if level.upper() == "INFO":
            logger.info(message)
        elif level.upper() == "WARNING":
            logger.warning(message)
        elif level.upper() == "ERROR":
            logger.error(message)
        elif level.upper() == "DEBUG":
            logger.debug(message)
    except Exception:
        # 로깅 실패 시 print로 폴백 (선택적)
        try:
            print(f"[{level.upper()}] {message}")
        except Exception:
            # print도 실패하면 조용히 무시
            pass


def create_session_with_retry(
    total_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Optional[List[int]] = None,
) -> requests.Session:
    """
    재시도 로직이 내장된 requests.Session 생성

    Args:
        total_retries: 총 재시도 횟수
        backoff_factor: 재시도 간격 배수 (0.5초 → 1초 → 2초 ...)
        status_forcelist: 재시도할 HTTP 상태 코드 목록

    Returns:
        requests.Session: 재시도 로직이 설정된 세션
    """
    if status_forcelist is None:
        status_forcelist = [500, 502, 503, 504, 408, 429]

    session = requests.Session()

    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


def send_api_event(
    url: str,
    event_data: Dict[str, Any],
    image_path: Optional[str] = None,
    timeout: int = 10,
    retry_count: int = 3,
    backoff_factor: float = 0.5,
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """
    통합 API 전송 함수 (동기 버전)

    Args:
        url: API 엔드포인트 URL
        event_data: 전송할 이벤트 데이터 (dict)
        image_path: 이미지 파일 경로 (선택적, multipart/form-data 사용)
        timeout: 요청 타임아웃 (초)
        retry_count: 재시도 횟수
        backoff_factor: 재시도 간격 배수
        raise_on_error: True면 에러 발생 시 예외 발생, False면 dict 반환

    Returns:
        dict: 전송 결과
            {
                "success": bool,
                "status_code": int | None,
                "response_text": str | None,
                "error": str | None,
                "timestamp": str,
                "retry_attempts": int
            }
    """
    result = {
        "success": False,
        "status_code": None,
        "response_text": None,
        "error": None,
        "timestamp": datetime.now().isoformat(),
        "retry_attempts": 0,
    }

    # 재시도 로직이 내장된 세션 생성
    session = create_session_with_retry(
        total_retries=retry_count,
        backoff_factor=backoff_factor,
    )

    try:
        # Multipart vs JSON 선택
        if image_path and Path(image_path).exists():
            # Multipart/form-data 전송
            _safe_log("INFO", f"[API] Multipart 전송 시작: {url}")

            # 이미지 파일 읽기
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()

                files = {
                    "image": (Path(image_path).name, image_data, "image/jpeg")
                }

                # 메타데이터는 form-data로 전송
                form_data = {}
                for key, value in event_data.items():
                    if isinstance(value, (dict, list)):
                        import json
                        form_data[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        form_data[key] = str(value)

                response = session.post(
                    url,
                    data=form_data,
                    files=files,
                    timeout=timeout
                )
            except FileNotFoundError:
                _safe_log("WARNING", f"[API] 이미지 파일 없음: {image_path}, JSON으로 폴백")
                # 파일 없으면 JSON으로 폴백
                response = session.post(
                    url,
                    json=event_data,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout
                )
        else:
            # JSON 전송
            _safe_log("INFO", f"[API] JSON 전송 시작: {url}")
            response = session.post(
                url,
                json=event_data,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )

        # 응답 처리
        result["status_code"] = response.status_code
        result["response_text"] = response.text[:500]  # 처음 500자만 저장

        if response.status_code == 200:
            result["success"] = True
            _safe_log("INFO", f"[API] ✅ 전송 성공: {url} (HTTP {response.status_code})")
        else:
            result["error"] = f"HTTP {response.status_code}"
            _safe_log("WARNING", f"[API] ⚠️ HTTP 오류: {url} (HTTP {response.status_code})")

    except requests.exceptions.Timeout as e:
        result["error"] = "Timeout"
        _safe_log("ERROR", f"[API] ⏱️ 타임아웃: {url} ({timeout}초)")
        if raise_on_error:
            raise

    except requests.exceptions.ConnectionError as e:
        result["error"] = "Connection Error"
        _safe_log("ERROR", f"[API] 🔌 연결 오류: {url} - {str(e)[:100]}")
        if raise_on_error:
            raise

    except requests.exceptions.RequestException as e:
        result["error"] = f"Request Error: {type(e).__name__}"
        _safe_log("ERROR", f"[API] ❌ 요청 오류: {url} - {str(e)[:100]}")
        if raise_on_error:
            raise

    except Exception as e:
        result["error"] = f"Unexpected Error: {type(e).__name__}"
        _safe_log("ERROR", f"[API] ❌ 예상치 못한 오류: {url} - {str(e)[:100]}")
        if raise_on_error:
            raise

    finally:
        session.close()

    return result


def send_api_event_async(
    url: str,
    event_data: Dict[str, Any],
    image_path: Optional[str] = None,
    timeout: int = 10,
    retry_count: int = 3,
    backoff_factor: float = 0.5,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Future:
    """
    통합 API 전송 함수 (비동기 버전)

    ThreadPoolExecutor를 사용하여 백그라운드에서 전송

    Args:
        url: API 엔드포인트 URL
        event_data: 전송할 이벤트 데이터 (dict)
        image_path: 이미지 파일 경로 (선택적)
        timeout: 요청 타임아웃 (초)
        retry_count: 재시도 횟수
        backoff_factor: 재시도 간격 배수
        callback: 완료 시 호출할 콜백 함수 (결과 dict를 인자로 받음)

    Returns:
        Future: concurrent.futures.Future 객체
            - result() 메서드로 결과 dict 가져오기
            - done() 메서드로 완료 여부 확인

    사용 예:
        future = send_api_event_async(url, data)
        # ... 다른 작업 ...
        result = future.result()  # 완료될 때까지 대기
    """
    global _executor

    # 스레드 풀 초기화 (최초 1회)
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=_executor_max_workers)
        _safe_log("INFO", f"[API] ThreadPoolExecutor 초기화 (max_workers={_executor_max_workers})")

    # 비동기 작업 제출
    future = _executor.submit(
        send_api_event,
        url=url,
        event_data=event_data,
        image_path=image_path,
        timeout=timeout,
        retry_count=retry_count,
        backoff_factor=backoff_factor,
        raise_on_error=False,  # 비동기에서는 예외 발생 안 함
    )

    # 콜백 등록 (선택적)
    if callback:
        def callback_wrapper(fut: Future):
            try:
                result = fut.result()
                callback(result)
            except Exception as e:
                _safe_log("ERROR", f"[API] 콜백 오류: {str(e)[:100]}")

        future.add_done_callback(callback_wrapper)

    return future


def send_to_multiple_endpoints(
    endpoints: List[Dict[str, Any]],
    event_data: Dict[str, Any],
    image_path: Optional[str] = None,
    timeout: int = 10,
    retry_count: int = 3,
    async_mode: bool = True,
) -> List[Dict[str, Any]]:
    """
    여러 API 엔드포인트에 동시 전송

    Args:
        endpoints: 엔드포인트 목록
            [
                {"name": "API1", "url": "http://...", "enabled": True},
                {"name": "API2", "url": "http://...", "enabled": False},
            ]
        event_data: 전송할 이벤트 데이터
        image_path: 이미지 파일 경로 (선택적)
        timeout: 요청 타임아웃 (초)
        retry_count: 재시도 횟수
        async_mode: True면 비동기 전송 (빠름), False면 순차 전송

    Returns:
        list: 각 엔드포인트의 전송 결과 리스트
            [
                {"endpoint_name": "API1", "result": {...}},
                {"endpoint_name": "API2", "result": {...}},
            ]
    """
    results = []
    futures = []

    # 활성화된 엔드포인트만 필터링
    active_endpoints = [ep for ep in endpoints if ep.get("enabled", True)]

    if not active_endpoints:
        _safe_log("WARNING", "[API] 활성화된 엔드포인트 없음")
        return results

    _safe_log("INFO", f"[API] {len(active_endpoints)}개 엔드포인트에 전송 시작")

    if async_mode:
        # 비동기 전송
        for ep in active_endpoints:
            future = send_api_event_async(
                url=ep["url"],
                event_data=event_data,
                image_path=image_path,
                timeout=timeout,
                retry_count=retry_count,
            )
            futures.append((ep["name"], future))

        # 모든 결과 수집
        for name, future in futures:
            try:
                result = future.result(timeout=timeout + 5)  # 여유 시간 추가
                results.append({
                    "endpoint_name": name,
                    "result": result,
                })
            except Exception as e:
                _safe_log("ERROR", f"[API] {name} 비동기 전송 실패: {str(e)[:100]}")
                results.append({
                    "endpoint_name": name,
                    "result": {
                        "success": False,
                        "error": f"Async Error: {type(e).__name__}",
                    },
                })
    else:
        # 동기 전송
        for ep in active_endpoints:
            result = send_api_event(
                url=ep["url"],
                event_data=event_data,
                image_path=image_path,
                timeout=timeout,
                retry_count=retry_count,
            )
            results.append({
                "endpoint_name": ep["name"],
                "result": result,
            })

    # 성공/실패 카운트
    success_count = sum(1 for r in results if r["result"].get("success"))
    _safe_log("INFO", f"[API] 전송 완료: {success_count}/{len(results)} 성공")

    return results


def cleanup_executor():
    """
    스레드 풀 정리 (앱 종료 시 호출)
    """
    global _executor
    if _executor is not None:
        _safe_log("INFO", "[API] ThreadPoolExecutor 종료 중...")
        _executor.shutdown(wait=True)
        _executor = None
        _safe_log("INFO", "[API] ThreadPoolExecutor 종료 완료")


# 프로그램 종료 시 자동 정리
import atexit
atexit.register(cleanup_executor)
