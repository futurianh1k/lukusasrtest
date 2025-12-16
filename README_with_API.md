# 음성인식 + API 관리 통합 패키지

RK3588 NPU 최적화 실시간 음성인식 시스템에 API 엔드포인트 관리 기능을 통합한 패키지입니다.

## 📦 패키지 구조

```
asr_with_api_package/
├── demo_vad_with_api.py         # 메인 실행 파일 (통합 UI)
├── api_endpoint_db.py            # SQLite DB 관리
├── api_utils.py                  # API 전송 유틸리티
├── emergency_alert_manager.py    # 응급 알림 관리자
├── api_management_ui.py          # API 관리 UI (Gradio)
├── mock_api_server.py            # Mock API 서버 (테스트용)
├── test_integration.py           # 통합 테스트
├── requirements.txt              # 필수 패키지
├── INTEGRATION_GUIDE.md          # 통합 가이드
├── README.md                     # 이 파일
├── data/                         # 데이터 디렉토리
│   └── api_endpoints.db          # API 엔드포인트 DB (자동 생성)
├── logs/                         # 로그 디렉토리
└── config/                       # 설정 디렉토리
```

## 🚀 빠른 시작

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 통합 시스템 실행

```bash
python demo_vad_with_api.py
```

### 3. 브라우저 접속

```
https://localhost:7860
```

## 🎯 주요 기능

### 1️⃣ 실시간 음성인식
- VAD 기반 자동 음성 감지
- 응급 키워드 자동 인식
- 채팅 스타일 결과 표시

### 2️⃣ API 엔드포인트 관리
- 엔드포인트 추가/수정/삭제
- 활성화/비활성화 토글
- 연결 테스트
- SQLite 기반 영구 저장

### 3️⃣ 응급 알림 전송
- 다중 엔드포인트 동시 전송 (비동기)
- 자동 재시도 로직
- 전송 결과 모니터링
- JSON / Multipart 자동 선택

## 📋 사용 시나리오

### 시나리오 1: 최초 설정

1. **Mock 서버 실행** (테스트용)
   ```bash
   # 터미널 1
   python mock_api_server.py
   ```

2. **통합 시스템 실행**
   ```bash
   # 터미널 2
   python demo_vad_with_api.py
   ```

3. **브라우저에서 설정**
   - `https://localhost:7860` 접속
   - "API 엔드포인트 관리" 탭 이동
   - Mock 서버 추가:
     - 이름: `Mock Server`
     - URL: `http://localhost:10008/api/emergency/quick`
     - 전송 타입: `JSON`
     - 활성화: 체크
   - "추가" 버튼 클릭

4. **설정 저장**
   - Watch ID: `watch_test_001`
   - Sender ID: `voice_asr_system`
   - "설정 저장" 클릭

5. **연결 테스트**
   - 엔드포인트 ID: `1`
   - "테스트" 버튼 클릭
   - Mock 서버 로그 확인

### 시나리오 2: 실제 서버 연결

1. **통합 시스템 실행**
   ```bash
   python demo_vad_with_api.py
   ```

2. **실제 API 엔드포인트 추가**
   - 이름: `Main API Server`
   - URL: `http://10.10.11.23:10008/api/emergency/quick`
   - 전송 타입: `JSON`
   - 활성화: 체크

3. **Watch ID 설정**
   - Watch ID: `watch_1760663070591_8022`
   - Sender ID: `voice_asr_system`

4. **음성인식 사용**
   - "실시간 음성인식" 탭 이동
   - 마이크 버튼 클릭
   - 말하기 시작
   - 응급 키워드 감지 시 자동 전송

### 시나리오 3: 다중 엔드포인트

1. **여러 엔드포인트 등록**
   - Main Server (활성화)
   - Backup Server (활성화)
   - Monitoring Server (활성화)

2. **응급 상황 발생**
   - 음성인식에서 응급 키워드 감지
   - 3개 엔드포인트에 동시 전송 (비동기)
   - 각 엔드포인트 전송 결과 확인

3. **결과 확인**
   - 전송 성공: 3/3
   - 모든 서버에서 응답 수신

## 🧪 테스트

### 자동 테스트

```bash
python test_integration.py
```

실행 내용:
1. 엔드포인트 추가/조회/수정
2. 설정 저장/조회
3. 응급 알림 전송
4. 엔드포인트 개별 테스트

### 수동 테스트

```bash
# Python 인터프리터
python

>>> from emergency_alert_manager import get_emergency_manager
>>> manager = get_emergency_manager()

# 엔드포인트 추가
>>> manager.add_endpoint(
...     name="Test Server",
...     url="http://localhost:10008/api/emergency/quick",
...     enabled=True
... )

# 응급 알림 전송
>>> result = manager.send_emergency_alert(
...     recognized_text="도와줘 사람이 쓰러졌어",
...     emergency_keywords=["도와줘", "쓰러졌어"]
... )
>>> print(f"성공: {result['success_count']}/{result['total_endpoints']}")
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

## ⚙️ 고급 설정

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

result = future.result()  # 완료 대기
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
1. 타임아웃 시간 증가
2. 네트워크 상태 확인

### HTTP 오류

**증상**: `HTTP 400/404/500`

**해결**:
1. URL 확인
2. API 서버 로그 확인
3. 데이터 형식 확인

### 모듈 없음

**증상**: `ModuleNotFoundError`

**해결**:
```bash
pip install -r requirements.txt
```

## 📚 상세 문서

- **INTEGRATION_GUIDE.md** - 통합 가이드
- **API_GUIDE.md** - API 사용 가이드

## 🔗 기존 프로젝트와 통합

### demo_vad_final.py 교체

```bash
# 백업
cp demo_vad_final.py demo_vad_final.py.backup

# 교체
cp demo_vad_with_api.py demo_vad_final.py
```

### 모듈 파일 복사

```bash
cp api_*.py emergency_alert_manager.py /path/to/your/project/
```

## 💡 팁

1. **개발 환경**: Mock 서버 사용
2. **프로덕션**: 실제 API 엔드포인트 등록
3. **백업**: 여러 엔드포인트 등록으로 이중화
4. **모니터링**: 전송 결과 로그 확인

## 🎓 학습 자료

### API 명세

**POST /api/emergency/quick**

요청:
```json
{
  "eventId": "string",
  "watchId": "string",
  "note": "응급 호출 발생",
  "recognizedText": "string",
  "emergencyKeywords": ["string"]
}
```

응답:
```json
{
  "status": "success",
  "message": "Event received"
}
```

## 📞 지원

문제 발생 시:
1. 로그 파일 확인: `./logs/app.log`
2. 테스트 실행: `python test_integration.py`
3. Mock 서버로 테스트: `python mock_api_server.py`

## 📝 라이선스

MIT License

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.
