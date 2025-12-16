# API 엔드포인트 관리 시스템 - 사용 가이드

## 📋 목차

1. [개요](#개요)
2. [설치 및 설정](#설치-및-설정)
3. [주요 기능](#주요-기능)
4. [사용 방법](#사용-방법)
5. [테스트 방법](#테스트-방법)
6. [문제 해결](#문제-해결)

---

## 개요

### 시스템 구성

음성 인식 시스템에서 응급 상황을 감지하면, 등록된 API 엔드포인트로 자동으로 알림을 전송하는 시스템입니다.

```
[음성 인식] → [응급 키워드 감지] → [API 엔드포인트 전송]
                                        ↓
                              [Main Server]
                              [Backup Server]
                              [Monitoring Server]
```

### 핵심 모듈

- **api_endpoint_db.py**: SQLite 기반 엔드포인트 저장소
- **api_utils.py**: 재시도 로직이 포함된 API 전송 유틸리티
- **emergency_alert_manager.py**: 응급 알림 관리자
- **api_management_ui.py**: Gradio 기반 관리 UI
- **test_integration.py**: 통합 테스트 스크립트
- **mock_api_server.py**: 테스트용 Mock 서버

---

## 설치 및 설정

### 1. 필수 패키지 설치

```bash
pip install requests gradio flask
```

### 2. 파일 구조

```
project/
├── api_endpoint_db.py          # DB 관리
├── api_utils.py                # API 전송 유틸리티
├── emergency_alert_manager.py  # 응급 알림 관리자
├── api_management_ui.py        # 관리 UI
├── test_integration.py         # 테스트 스크립트
├── mock_api_server.py          # Mock 서버
└── data/
    └── api_endpoints.db        # DB 파일 (자동 생성)
```

### 3. 초기 설정

프로그램 최초 실행 시 자동으로 설정됩니다:
- DB 파일 생성: `./data/api_endpoints.db`
- 기본 Watch ID: `watch_default_001`
- 기본 Sender ID: `voice_asr_system`

---

## 주요 기능

### 1. API 엔드포인트 관리

- ✅ 엔드포인트 추가/수정/삭제
- ✅ 활성화/비활성화 토글
- ✅ 엔드포인트 연결 테스트
- ✅ 재시작 후에도 설정 유지 (SQLite DB)

### 2. 응급 알림 전송

- ✅ 다중 엔드포인트 동시 전송 (비동기)
- ✅ 자동 재시도 (exponential backoff)
- ✅ JSON / Multipart 자동 선택
- ✅ 타임아웃 및 에러 처리

### 3. 전송 데이터 구조

```json
{
  "eventId": "uuid",
  "watchId": "watch_1760663070591_8022",
  "senderId": "voice_asr_system",
  "eventType": "emergency_voice",
  "note": "응급 호출 발생",
  "recognizedText": "도와줘 사람이 쓰러졌어",
  "emergencyKeywords": ["도와줘", "쓰러졌어"],
  "timestamp": "2025-12-16T14:30:00",
  "status": 1
}
```

---

## 사용 방법

### 방법 1: Gradio UI 사용 (권장)

#### 1단계: 서버 실행

```bash
python demo_vad_final.py
```

#### 2단계: 웹 브라우저 접속

```
https://localhost:7860
```

#### 3단계: "API 엔드포인트 관리" 탭 이동

#### 4단계: 엔드포인트 추가

1. "새 엔드포인트 추가" 섹션으로 이동
2. 필드 입력:
   - **이름**: `Main API Server`
   - **URL**: `http://10.10.11.23:10008/api/emergency/quick`
   - **전송 타입**: `JSON`
   - **활성화**: 체크
3. "추가" 버튼 클릭

#### 5단계: 설정 저장

1. "전역 설정" 섹션으로 이동
2. 필드 입력:
   - **Watch ID**: `watch_1760663070591_8022`
   - **Sender ID**: `voice_asr_system`
3. "설정 저장" 버튼 클릭

#### 6단계: 연결 테스트

1. "엔드포인트 관리" 섹션으로 이동
2. **엔드포인트 ID** 입력 (예: `1`)
3. "테스트" 버튼 클릭
4. 결과 확인

### 방법 2: Python 코드 사용

```python
from emergency_alert_manager import get_emergency_manager

# 매니저 가져오기
manager = get_emergency_manager()

# 엔드포인트 추가
endpoint_id = manager.add_endpoint(
    name="Main API Server",
    url="http://10.10.11.23:10008/api/emergency/quick",
    endpoint_type="json",
    enabled=True
)

# 설정 저장
manager.set_watch_id("watch_1760663070591_8022")
manager.set_sender_id("voice_asr_system")

# 응급 알림 전송
result = manager.send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)

print(f"전송 성공: {result['success']}")
print(f"성공/실패: {result['success_count']}/{result['failed_count']}")
```

---

## 테스트 방법

### 방법 1: Mock 서버 사용 (권장)

#### 1단계: Mock 서버 실행

```bash
# 터미널 1
python mock_api_server.py
```

출력:
```
🚀 Mock API 서버 시작
📍 서버 정보:
   - 주소: http://0.0.0.0:10008
   - 웹 UI: http://localhost:10008
   - 응급 알림 엔드포인트: /api/emergency/quick
```

#### 2단계: 엔드포인트 등록

```bash
# 터미널 2
python
```

```python
from emergency_alert_manager import get_emergency_manager

manager = get_emergency_manager()
manager.add_endpoint(
    name="Mock Server",
    url="http://localhost:10008/api/emergency/quick",
    endpoint_type="json",
    enabled=True
)
```

#### 3단계: 테스트 전송

```python
result = manager.send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)
```

#### 4단계: Mock 서버 로그 확인

터미널 1에서 수신 로그 확인:
```
🚨 응급 알림 수신!
================================================================================

📦 JSON 데이터:
{
  "eventId": "abc-123",
  "recognizedText": "도와줘 사람이 쓰러졌어",
  ...
}
```

### 방법 2: 통합 테스트 스크립트

```bash
python test_integration.py
```

실행 내용:
1. 엔드포인트 추가/조회/수정 테스트
2. 설정 저장/조회 테스트
3. 응급 알림 전송 테스트
4. 엔드포인트 개별 테스트

### 방법 3: curl 명령어 직접 테스트

```bash
curl -X POST http://localhost:10008/api/emergency/quick \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "test-123",
    "watchId": "watch_test",
    "note": "응급 호출 발생",
    "recognizedText": "도와줘 사람이 쓰러졌어"
  }'
```

---

## 문제 해결

### 1. 연결 오류 (Connection Error)

**증상**: `Connection Error` 또는 `연결 거부됨`

**원인**:
- API 서버가 실행 중이 아님
- 방화벽이 포트를 차단함
- URL이 잘못됨

**해결**:
1. API 서버가 실행 중인지 확인
2. 방화벽 설정 확인
3. URL 형식 확인 (`http://` 또는 `https://` 포함)

### 2. 타임아웃 (Timeout)

**증상**: `Timeout` 오류

**원인**:
- 서버 응답이 느림
- 네트워크 지연

**해결**:
1. 타임아웃 시간 증가:
   ```python
   manager.send_emergency_alert(..., timeout=30)
   ```
2. 네트워크 상태 확인

### 3. HTTP 4xx/5xx 오류

**증상**: `HTTP 400`, `HTTP 404`, `HTTP 500` 등

**원인**:
- 잘못된 URL 또는 엔드포인트
- 서버 측 오류
- 데이터 형식 불일치

**해결**:
1. URL 확인
2. API 서버 로그 확인
3. 데이터 형식 확인 (JSON vs Multipart)

### 4. 엔드포인트가 비활성화됨

**증상**: 전송되지 않음

**원인**:
- 엔드포인트가 비활성화 상태

**해결**:
1. UI에서 "활성화" 버튼 클릭
2. 또는 코드로:
   ```python
   manager.update_endpoint(endpoint_id, enabled=True)
   ```

### 5. DB 파일 권한 오류

**증상**: `Permission denied` 또는 `database is locked`

**원인**:
- DB 파일 권한 문제
- 다중 프로세스 동시 접근

**해결**:
1. DB 파일 권한 확인:
   ```bash
   chmod 666 ./data/api_endpoints.db
   ```
2. 동시 접근 제한

---

## 고급 설정

### 재시도 설정 커스터마이징

```python
from api_utils import send_api_event

result = send_api_event(
    url="http://...",
    event_data={...},
    timeout=10,           # 타임아웃 (초)
    retry_count=5,        # 재시도 횟수
    backoff_factor=1.0,   # 재시도 간격 배수
)
```

### 비동기 전송

```python
from api_utils import send_api_event_async

future = send_api_event_async(
    url="http://...",
    event_data={...},
)

# 다른 작업 수행...

# 결과 대기
result = future.result()
```

### 이미지 첨부

```python
result = manager.send_emergency_alert(
    recognized_text="...",
    emergency_keywords=["..."],
    image_path="/path/to/image.jpg"  # 이미지 경로
)
```

---

## 참고 자료

### API 명세

**POST /api/emergency/quick**

요청:
```json
{
  "eventId": "string (UUID)",
  "watchId": "string",
  "senderId": "string",
  "eventType": "string",
  "note": "string",
  "recognizedText": "string",
  "emergencyKeywords": ["string"],
  "timestamp": "string (ISO 8601)",
  "status": 1
}
```

응답 (200 OK):
```json
{
  "status": "success",
  "message": "Event received"
}
```

### 로깅

로그 레벨 변경:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 문의

문제가 지속되면 시스템 로그를 확인하세요:
```bash
tail -f app.log
```
