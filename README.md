# 응급 상황 API 전송 시스템

음성 인식 시스템에서 응급 상황을 감지하고, 등록된 API 엔드포인트로 자동 알림을 전송하는 통합 시스템입니다.

## 🚀 빠른 시작

### 1. Mock 서버 실행 (테스트용)

```bash
# 터미널 1
python mock_api_server.py
```

### 2. 통합 테스트

```bash
# 터미널 2
python test_integration.py
```

### 3. 음성 인식 시스템 실행

```bash
# 터미널 3
python demo_vad_final.py
```

웹 브라우저에서 접속: `https://localhost:7860`

## 📦 파일 구조

```
.
├── api_endpoint_db.py           # SQLite DB 관리
├── api_utils.py                 # API 전송 유틸리티 (재시도, 비동기)
├── emergency_alert_manager.py   # 응급 알림 관리자
├── api_management_ui.py         # Gradio 관리 UI
├── test_integration.py          # 통합 테스트
├── mock_api_server.py           # Mock API 서버 (Flask)
├── API_GUIDE.md                 # 상세 사용 가이드
└── README.md                    # 이 파일
```

## 🎯 주요 기능

### 1. API 엔드포인트 관리
- ✅ 엔드포인트 추가/수정/삭제
- ✅ 활성화/비활성화 토글
- ✅ 연결 테스트
- ✅ SQLite 기반 영구 저장

### 2. 응급 알림 전송
- ✅ 다중 엔드포인트 동시 전송 (비동기)
- ✅ 자동 재시도 (exponential backoff)
- ✅ JSON / Multipart 자동 선택
- ✅ 타임아웃 및 에러 처리

### 3. Gradio UI
- ✅ 엔드포인트 목록 조회
- ✅ 엔드포인트 관리 (추가/삭제/토글)
- ✅ 연결 테스트
- ✅ Watch ID / Sender ID 설정

## 🔧 설치

### 필수 패키지

```bash
pip install requests gradio flask
```

### 선택적 패키지 (음성 인식용)

```bash
pip install sherpa-onnx numpy
```

## 📖 사용 방법

### 방법 1: Gradio UI (권장)

1. **서버 실행**
   ```bash
   python demo_vad_final.py
   ```

2. **브라우저 접속**
   ```
   https://localhost:7860
   ```

3. **"API 엔드포인트 관리" 탭 이동**

4. **엔드포인트 추가**
   - 이름: `Main API Server`
   - URL: `http://10.10.11.23:10008/api/emergency/quick`
   - 전송 타입: `JSON`
   - 활성화: 체크
   - "추가" 버튼 클릭

5. **설정 저장**
   - Watch ID: `watch_1760663070591_8022`
   - Sender ID: `voice_asr_system`
   - "설정 저장" 버튼 클릭

6. **연결 테스트**
   - 엔드포인트 ID 입력
   - "테스트" 버튼 클릭

### 방법 2: Python 코드

```python
from emergency_alert_manager import get_emergency_manager

# 매니저 가져오기
manager = get_emergency_manager()

# 엔드포인트 추가
manager.add_endpoint(
    name="Main API Server",
    url="http://10.10.11.23:10008/api/emergency/quick",
    endpoint_type="json",
    enabled=True
)

# 설정
manager.set_watch_id("watch_1760663070591_8022")
manager.set_sender_id("voice_asr_system")

# 응급 알림 전송
result = manager.send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)

print(f"전송 성공: {result['success']}")
print(f"성공: {result['success_count']}개")
print(f"실패: {result['failed_count']}개")
```

## 🧪 테스트

### 1. Mock 서버 테스트

```bash
# 터미널 1: Mock 서버 실행
python mock_api_server.py

# 터미널 2: 테스트 실행
python test_integration.py
```

### 2. 실제 서버 테스트

```bash
# 엔드포인트 추가
python
>>> from emergency_alert_manager import get_emergency_manager
>>> manager = get_emergency_manager()
>>> manager.add_endpoint(
...     name="Real Server",
...     url="http://10.10.11.23:10008/api/emergency/quick",
...     enabled=True
... )

# 테스트 전송
>>> result = manager.send_emergency_alert(
...     recognized_text="테스트 메시지",
...     emergency_keywords=["테스트"]
... )
>>> print(result)
```

### 3. curl 테스트

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

## 📊 전송 데이터 구조

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

## 🔌 API 명세

### POST /api/emergency/quick

**요청**:
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

**응답 (200 OK)**:
```json
{
  "status": "success",
  "message": "Event received"
}
```

## ⚙️ 설정

### 재시도 설정

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

# 다른 작업...

result = future.result()
```

### 이미지 첨부

```python
result = manager.send_emergency_alert(
    recognized_text="...",
    emergency_keywords=["..."],
    image_path="/path/to/image.jpg"
)
```

## 🛠️ 문제 해결

### 연결 오류

**증상**: `Connection Error`

**해결**:
1. API 서버 실행 여부 확인
2. 방화벽 설정 확인
3. URL 형식 확인 (`http://` 포함)

### 타임아웃

**증상**: `Timeout`

**해결**:
1. 타임아웃 시간 증가:
   ```python
   manager.send_emergency_alert(..., timeout=30)
   ```
2. 네트워크 상태 확인

### HTTP 오류

**증상**: `HTTP 400/404/500`

**해결**:
1. URL 확인
2. API 서버 로그 확인
3. 데이터 형식 확인

### 엔드포인트 비활성화

**증상**: 전송 안 됨

**해결**:
1. UI에서 "활성화" 버튼 클릭
2. 또는:
   ```python
   manager.update_endpoint(endpoint_id, enabled=True)
   ```

## 📚 상세 문서

더 자세한 내용은 [API_GUIDE.md](API_GUIDE.md)를 참조하세요.

## 🔗 통합 방법

### demo_vad_final.py와 통합

기존 `emergency_alert.py` 모듈을 새로운 `emergency_alert_manager.py`로 교체:

```python
# 기존 코드 (emergency_alert.py)
from emergency_alert import send_emergency_alert

# 새 코드 (emergency_alert_manager.py)
from emergency_alert_manager import send_emergency_alert

# 사용법은 동일
send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)
```

추가로 `api_management_ui.py`의 탭을 Gradio UI에 추가:

```python
from api_management_ui import create_api_management_tab

with gr.Blocks() as demo:
    # 기존 탭들...
    
    # API 관리 탭 추가
    create_api_management_tab()
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 📧 문의

문제가 있으면 시스템 로그를 확인하세요:
```bash
tail -f app.log
```
