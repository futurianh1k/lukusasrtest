# demo_vad_final.py 통합 가이드

기존 `demo_vad_final.py`에 API 엔드포인트 관리 기능을 통합하는 방법을 설명합니다.

## 📋 통합 전/후 비교

### 통합 전 (기존)

```
demo_vad_final.py (메인)
├── config.py
├── model_loader.py
├── vad_processor.py
├── matcher.py
├── emergency_alert.py         ← 하드코딩된 API 설정
├── session_manager.py
├── report_generator.py
├── utils.py
├── gradio_handlers.py
└── gradio_ui.py
```

**문제점:**
- API 엔드포인트가 하드코딩됨
- 재시작하면 설정이 초기화됨
- 단일 엔드포인트만 지원
- 재시도 로직 없음
- UI에서 설정 변경 불가

### 통합 후 (신규)

```
demo_vad_with_api.py (메인)
├── config.py
├── model_loader.py
├── vad_processor.py
├── matcher.py
├── emergency_alert_manager.py  ← 새로운 관리자
│   ├── api_endpoint_db.py      ← SQLite DB 관리
│   ├── api_utils.py            ← 재시도 + 비동기 전송
│   └── api_management_ui.py    ← Gradio UI
├── session_manager.py
├── report_generator.py
├── utils.py
├── gradio_handlers.py
└── gradio_ui.py
```

**개선점:**
- ✅ 다중 엔드포인트 지원
- ✅ SQLite 기반 영구 저장
- ✅ 자동 재시도 로직
- ✅ UI에서 실시간 설정 변경
- ✅ 비동기 전송

## 🔧 통합 방법

### 방법 1: 완전 교체 (권장)

기존 파일을 백업하고 새 통합 버전으로 교체합니다.

```bash
# 1. 백업
cp demo_vad_final.py demo_vad_final.py.backup
cp emergency_alert.py emergency_alert.py.backup

# 2. 새 파일 복사
cp demo_vad_with_api.py demo_vad_final.py
cp api_endpoint_db.py .
cp api_utils.py .
cp emergency_alert_manager.py .
cp api_management_ui.py .

# 3. 실행
python demo_vad_final.py
```

### 방법 2: 점진적 통합

기존 프로젝트 구조를 유지하면서 점진적으로 통합합니다.

#### 단계 1: API 모듈 추가

```bash
# 프로젝트 디렉토리에 API 모듈 복사
cp api_endpoint_db.py /path/to/your/project/
cp api_utils.py /path/to/your/project/
cp emergency_alert_manager.py /path/to/your/project/
cp api_management_ui.py /path/to/your/project/
```

#### 단계 2: emergency_alert.py 수정

기존 `emergency_alert.py`를 수정하여 새 관리자를 사용하도록 변경:

```python
# emergency_alert.py (수정)

from emergency_alert_manager import get_emergency_manager

def send_emergency_alert(recognized_text, emergency_keywords):
    """
    응급 알림 전송 (새 버전)
    """
    manager = get_emergency_manager()
    
    result = manager.send_emergency_alert(
        recognized_text=recognized_text,
        emergency_keywords=emergency_keywords,
    )
    
    return result
```

#### 단계 3: gradio_ui.py 수정

Gradio UI에 API 관리 탭 추가:

```python
# gradio_ui.py (수정)

from api_management_ui import create_api_management_tab

def create_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# 음성인식 시스템")
        
        with gr.Tabs():
            # 기존 탭들...
            with gr.Tab("🎤 실시간 음성인식"):
                # ... 기존 코드 ...
                pass
            
            # 새 탭 추가
            create_api_management_tab()
            
    return demo
```

#### 단계 4: 테스트

```bash
python demo_vad_final.py
```

브라우저에서 `https://localhost:7860` 접속 후:
1. "API 엔드포인트 관리" 탭 확인
2. 테스트 엔드포인트 추가
3. 연결 테스트

### 방법 3: 새 프로젝트로 시작

완전히 새로운 프로젝트로 시작:

```bash
# 통합 패키지 사용
cd asr_with_api_package
python demo_vad_with_api.py
```

## 📝 코드 수정 가이드

### 1. 기존 emergency_alert.py 함수 호출

**변경 전:**
```python
from emergency_alert import send_emergency_alert

result = send_emergency_alert(
    recognized_text="도와줘",
    emergency_keywords=["도와줘"],
)
```

**변경 후:**
```python
from emergency_alert_manager import send_emergency_alert

# 사용법은 동일
result = send_emergency_alert(
    recognized_text="도와줘",
    emergency_keywords=["도와줘"],
)

# 추가 기능 사용
print(f"전송 성공: {result['success']}")
print(f"성공/실패: {result['success_count']}/{result['failed_count']}")
```

### 2. 엔드포인트 프로그래밍 방식 추가

**초기 설정 코드 추가:**
```python
# demo_vad_final.py 또는 config.py

from emergency_alert_manager import get_emergency_manager

def init_api_endpoints():
    """
    초기 API 엔드포인트 설정
    """
    manager = get_emergency_manager()
    
    # 기존 엔드포인트 확인
    endpoints = manager.list_endpoints()
    
    # 없으면 기본 엔드포인트 추가
    if not endpoints:
        manager.add_endpoint(
            name="Main Server",
            url="http://10.10.11.23:10008/api/emergency/quick",
            endpoint_type="json",
            enabled=True
        )
        
        manager.set_watch_id("watch_1760663070591_8022")
        manager.set_sender_id("voice_asr_system")

# 메인 실행 시 호출
if __name__ == "__main__":
    init_api_endpoints()
    # ... 나머지 코드 ...
```

### 3. 응급 상황 감지 부분 수정

기존 VAD 프로세서나 핸들러에서 응급 알림을 보내는 부분:

**변경 전:**
```python
if is_emergency:
    # 하드코딩된 API 호출
    requests.post(
        "http://10.10.11.23:10008/api/emergency/quick",
        json={"note": "응급 호출 발생", ...}
    )
```

**변경 후:**
```python
if is_emergency:
    from emergency_alert_manager import send_emergency_alert
    
    # 등록된 모든 엔드포인트에 자동 전송
    result = send_emergency_alert(
        recognized_text=text,
        emergency_keywords=keywords,
    )
    
    # 결과 로깅
    logger.info(f"응급 알림 전송: {result['success_count']}/{result['total_endpoints']} 성공")
```

## 🧪 통합 후 테스트

### 1. 기본 기능 테스트

```bash
# Mock 서버 실행
python mock_api_server.py

# 메인 시스템 실행 (다른 터미널)
python demo_vad_final.py
```

### 2. UI 테스트

브라우저 접속 후:
1. ✅ "실시간 음성인식" 탭 동작 확인
2. ✅ "API 엔드포인트 관리" 탭 표시 확인
3. ✅ 엔드포인트 추가/삭제 테스트
4. ✅ 연결 테스트 기능 확인

### 3. 응급 알림 테스트

```python
# Python 인터프리터에서
from emergency_alert_manager import send_emergency_alert

result = send_emergency_alert(
    recognized_text="도와줘 사람이 쓰러졌어",
    emergency_keywords=["도와줘", "쓰러졌어"]
)

print(result)
```

### 4. 통합 테스트

```bash
python test_integration.py
```

## 🔄 마이그레이션 체크리스트

- [ ] API 모듈 파일 복사
- [ ] requirements.txt 업데이트
- [ ] emergency_alert.py 수정
- [ ] gradio_ui.py에 API 관리 탭 추가
- [ ] 초기 설정 코드 추가
- [ ] Mock 서버로 테스트
- [ ] 실제 API 서버로 테스트
- [ ] 로그 확인
- [ ] 에러 처리 확인

## ⚠️ 주의사항

### 1. 하위 호환성

기존 코드와의 하위 호환성을 위해 `emergency_alert.py`를 wrapper로 유지:

```python
# emergency_alert.py (Wrapper)

from emergency_alert_manager import send_emergency_alert as _send_alert

def send_emergency_alert(recognized_text, emergency_keywords):
    """
    하위 호환성을 위한 wrapper
    """
    result = _send_alert(recognized_text, emergency_keywords)
    
    # 기존 코드가 기대하는 형식으로 변환 (필요시)
    return {
        'success': result.get('success'),
        'message': f"{result['success_count']}/{result['total_endpoints']} sent"
    }
```

### 2. 데이터베이스 위치

DB 파일 경로를 프로젝트에 맞게 조정:

```python
# config.py에 추가
API_DB_PATH = "./data/api_endpoints.db"

# emergency_alert_manager.py에서 사용
manager = EmergencyAlertManager(db_path=API_DB_PATH)
```

### 3. 로깅 레벨

API 모듈의 로깅이 너무 verbose하면:

```python
import logging
logging.getLogger('api_utils').setLevel(logging.WARNING)
logging.getLogger('emergency_alert_manager').setLevel(logging.INFO)
```

## 📊 성능 영향

### 리소스 사용량

**통합 전:**
- 메모리: ~100MB
- CPU: 1-2 코어

**통합 후:**
- 메모리: ~120MB (+20MB, SQLite + 스레드 풀)
- CPU: 1-2 코어 (변화 없음, 비동기 처리)

### 응답 시간

- **동기 전송**: ~100-500ms (단일 엔드포인트)
- **비동기 전송**: ~100-200ms (다중 엔드포인트)
  - 3개 엔드포인트에 동시 전송해도 단일 전송과 비슷한 시간

## 🆘 문제 해결

### 모듈을 찾을 수 없음

```bash
ModuleNotFoundError: No module named 'api_endpoint_db'
```

**해결:**
```bash
# 현재 디렉토리에 모듈 파일이 있는지 확인
ls -l api_*.py emergency_alert_manager.py

# 없으면 복사
cp /path/to/api_*.py .
cp /path/to/emergency_alert_manager.py .
```

### DB 권한 오류

```bash
sqlite3.OperationalError: unable to open database file
```

**해결:**
```bash
# data 디렉토리 생성
mkdir -p data

# 권한 설정
chmod 755 data
```

### Gradio 탭이 표시 안 됨

**원인:** `api_management_ui.py` import 실패

**해결:**
```python
# demo_vad_final.py에서 안전한 import
try:
    from api_management_ui import create_api_management_tab
    API_UI_AVAILABLE = True
except ImportError:
    API_UI_AVAILABLE = False

# UI 생성 시
if API_UI_AVAILABLE:
    create_api_management_tab()
else:
    with gr.Tab("⚙️ API 관리"):
        gr.Markdown("API 관리 모듈을 사용할 수 없습니다.")
```

## 📚 추가 자료

- **API_GUIDE.md** - API 사용 상세 가이드
- **README.md** - 패키지 개요
- **test_integration.py** - 테스트 예제 코드

## 💬 피드백

통합 과정에서 문제가 발생하면:
1. 로그 파일 확인: `./logs/app.log`
2. 테스트 실행: `python test_integration.py`
3. Mock 서버로 격리 테스트
