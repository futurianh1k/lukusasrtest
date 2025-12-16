# 🚀 빠른 시작 가이드

demo_vad_final.py에 API 엔드포인트 관리 기능을 통합한 패키지입니다.

## ⚡ 5분 안에 시작하기

### 1️⃣ 패키지 압축 해제

```bash
tar -xzf asr_with_api_package.tar.gz
cd asr_with_api_package
```

### 2️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

### 3️⃣ Mock 서버 실행 (테스트용)

```bash
# 터미널 1
python mock_api_server.py
```

출력:
```
🚀 Mock API 서버 시작
📍 주소: http://0.0.0.0:10008
📍 엔드포인트: /api/emergency/quick
```

### 4️⃣ 통합 시스템 실행

```bash
# 터미널 2
python demo_vad_with_api.py
```

출력:
```
🚀 Sherpa-ONNX Sense-Voice 음성인식 UI 시작
🖥️ RK3588 NPU 최적화 (v6 - API 통합)
✅ API 관리 모듈 로드 완료
✅ 응급 알림 관리자 초기화 완료
🌐 웹 서버 시작...
📍 접속 주소: https://localhost:7860
```

### 5️⃣ 브라우저 접속

```
https://localhost:7860
```

또는 (SSL 오류 시):
```
http://localhost:7860
```

### 6️⃣ API 엔드포인트 추가

1. **"API 엔드포인트 관리" 탭** 클릭

2. **"새 엔드포인트 추가"** 섹션에서:
   - 이름: `Mock Server`
   - URL: `http://localhost:10008/api/emergency/quick`
   - 전송 타입: `JSON`
   - 활성화: ✅ 체크

3. **"추가" 버튼** 클릭

### 7️⃣ 설정 저장

1. **"전역 설정"** 섹션으로 스크롤

2. 입력:
   - Watch ID: `watch_test_001`
   - Sender ID: `voice_asr_system`

3. **"설정 저장" 버튼** 클릭

### 8️⃣ 연결 테스트

1. **"엔드포인트 관리"** 섹션으로 이동

2. **엔드포인트 ID**: `1` 입력

3. **"🧪 테스트" 버튼** 클릭

4. **터미널 1 (Mock 서버)** 에서 수신 확인:
   ```
   🚨 응급 알림 수신!
   📦 JSON 데이터:
   {
     "eventId": "...",
     "note": "API 연결 테스트",
     ...
   }
   ```

## ✅ 완료!

이제 시스템이 준비되었습니다!

## 📋 다음 단계

### 실제 API 서버 연결

```bash
# 브라우저에서 "API 엔드포인트 관리" 탭
```

1. **새 엔드포인트 추가**:
   - 이름: `Main API Server`
   - URL: `http://10.10.11.23:10008/api/emergency/quick`
   - 전송 타입: `JSON`
   - 활성화: ✅

2. **Watch ID 업데이트**:
   - Watch ID: `watch_1760663070591_8022`

3. **연결 테스트**

### 음성인식 사용 (모델 필요)

실제 음성인식을 사용하려면:

1. Sherpa-ONNX 모델 파일 다운로드
2. 모델 경로 설정
3. "실시간 음성인식" 탭에서 마이크 사용

## 🧪 자동 테스트

```bash
python test_integration.py
```

실행 내용:
1. ✅ 엔드포인트 추가/조회/수정
2. ✅ 설정 저장/조회
3. ✅ 응급 알림 전송 테스트
4. ✅ 연결 테스트

## 🐍 Python 코드로 사용

```python
from emergency_alert_manager import get_emergency_manager

# 매니저 가져오기
manager = get_emergency_manager()

# 엔드포인트 추가
manager.add_endpoint(
    name="Test Server",
    url="http://localhost:10008/api/emergency/quick",
    enabled=True
)

# 응급 알림 전송
result = manager.send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)

print(f"전송 결과: {result['success_count']}/{result['total_endpoints']} 성공")
```

## 📊 전송 데이터 예시

시스템이 전송하는 JSON 데이터:

```json
{
  "eventId": "abc-123-def-456",
  "watchId": "watch_test_001",
  "senderId": "voice_asr_system",
  "eventType": "emergency_voice",
  "note": "응급 호출 발생",
  "recognizedText": "도와줘 사람이 쓰러졌어",
  "emergencyKeywords": ["도와줘", "쓰러졌어"],
  "timestamp": "2025-12-16T14:30:00",
  "status": 1
}
```

## 🛠️ 문제 해결

### 연결 오류

**증상**: "Connection Error"

**해결**:
```bash
# Mock 서버가 실행 중인지 확인
ps aux | grep mock_api_server.py

# 없으면 실행
python mock_api_server.py
```

### 포트 충돌

**증상**: "Address already in use"

**해결**:
```bash
# 다른 포트 사용
python demo_vad_with_api.py --port 7861
```

### 모듈 없음

**증상**: "ModuleNotFoundError"

**해결**:
```bash
pip install -r requirements.txt
```

## 📚 상세 문서

- **README.md** - 전체 개요
- **INTEGRATION_GUIDE.md** - 기존 프로젝트 통합 방법
- **API_GUIDE.md** - API 사용 상세 가이드

## 💡 주요 특징

### ✨ 새로운 기능

1. **다중 엔드포인트**
   - Main Server, Backup Server 동시 운영
   - 개별 활성화/비활성화

2. **자동 재시도**
   - 실패 시 자동 재전송
   - Exponential backoff

3. **영구 저장**
   - SQLite 기반 DB
   - 재시작 후에도 설정 유지

4. **실시간 관리**
   - 웹 UI에서 즉시 설정 변경
   - 재시작 불필요

5. **비동기 전송**
   - 여러 서버에 동시 전송
   - 빠른 응답 시간

## 🎯 사용 시나리오

### 개발 환경

```bash
# Mock 서버 사용
python mock_api_server.py
python demo_vad_with_api.py
```

### 테스트 환경

```bash
# 실제 API 서버 + Backup
엔드포인트 1: http://test-server.com/api/emergency
엔드포인트 2: http://backup-server.com/api/emergency
```

### 프로덕션 환경

```bash
# Main + Backup + Monitoring
엔드포인트 1: http://10.10.11.23:10008/api/emergency/quick
엔드포인트 2: http://10.10.11.24:10008/api/emergency/quick
엔드포인트 3: http://monitoring.com/api/events
```

## 🔗 유용한 링크

- Mock 서버: http://localhost:10008
- 메인 UI: https://localhost:7860
- API 문서: ./API_GUIDE.md

## 📞 지원

문제 발생 시:

1. **로그 확인**
   ```bash
   tail -f logs/app.log
   ```

2. **테스트 실행**
   ```bash
   python test_integration.py
   ```

3. **Mock 서버로 격리 테스트**
   ```bash
   python mock_api_server.py
   ```

---

## 🎉 축하합니다!

통합이 완료되었습니다. 이제 강력한 API 관리 기능과 함께 음성인식 시스템을 사용하세요!
