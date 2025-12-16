# ASR WebSocket API 서버 가이드

Sherpa-ONNX 기반 실시간 음성인식 WebSocket API 서버

---

## 📋 목차

1. [개요](#개요)
2. [설치](#설치)
3. [서버 실행](#서버-실행)
4. [API 문서](#api-문서)
5. [WebSocket 프로토콜](#websocket-프로토콜)
6. [사용 예제](#사용-예제)
7. [문제 해결](#문제-해결)

---

## 🎯 개요

ASR WebSocket API 서버는 Sherpa-ONNX 음성인식 엔진을 WebSocket 기반 실시간 API로 제공합니다.

### 주요 기능

- ✅ **WebSocket 기반 실시간 오디오 스트리밍**
- ✅ **VAD (Voice Activity Detection) 자동 음성 구간 감지**
- ✅ **다중 세션 관리** (여러 클라이언트 동시 지원)
- ✅ **응급 상황 자동 감지 및 알림**
- ✅ **RESTful API** (세션 관리, 상태 조회)
- ✅ **RK3588 NPU 최적화**

### 아키텍처

```
[CoreS3/Client] ─── WebSocket ───> [ASR API Server] ─── [Sherpa-ONNX]
                                           │
                                           └──> [VAD Processor]
                                           └──> [Emergency Detector]
```

---

## 🔧 설치

### 1. 기본 요구사항

- Python 3.8 이상
- Sherpa-ONNX (RK3588 버전)
- 음성인식 모델 (models/ 디렉토리)

### 2. 의존성 설치

```bash
# 기존 demo_vad_final.py 의존성
pip install -r requirements.txt

# API 서버 추가 의존성
pip install -r requirements_api.txt
```

### 3. 모델 다운로드

```bash
# models/ 디렉토리에 Sherpa-ONNX 모델 배치
ls models/sherpa-onnx-rk3588-30-seconds-sense-voice-zh-en-ja-ko-yue-2024-07-17/
# model.rknn
# tokens.txt
```

---

## 🚀 서버 실행

### 기본 실행

```bash
python asr_api_server.py
```

### 옵션 지정

```bash
# 호스트와 포트 지정
python asr_api_server.py --host 0.0.0.0 --port 8001

# RK3588 NPU 4코어 사용 (권장)
taskset 0x0F python asr_api_server.py
```

### 실행 확인

```bash
# 헬스 체크
curl http://localhost:8001/health

# 서버 정보
curl http://localhost:8001/
```

---

## 📚 API 문서

### 1. 세션 시작

**`POST /asr/session/start`**

새로운 음성인식 세션을 생성합니다.

**요청 Body:**

```json
{
  "device_id": "cores3_01",
  "language": "auto",
  "sample_rate": 16000,
  "vad_enabled": true
}
```

**응답:**

```json
{
  "session_id": "uuid-xxxx-xxxx",
  "ws_url": "ws://localhost:8001/ws/asr/uuid-xxxx-xxxx",
  "status": "ready",
  "message": "세션이 생성되었습니다. WebSocket으로 연결하세요."
}
```

### 2. 세션 상태 조회

**`GET /asr/session/{session_id}/status`**

세션 상태를 조회합니다.

**응답:**

```json
{
  "session_id": "uuid-xxxx",
  "device_id": "cores3_01",
  "is_active": true,
  "is_processing": false,
  "segments_count": 5,
  "last_result": "안녕하세요",
  "created_at": "2025-12-08T10:30:00",
  "language": "auto"
}
```

### 3. 세션 종료

**`POST /asr/session/{session_id}/stop`**

세션을 종료합니다.

**응답:**

```json
{
  "session_id": "uuid-xxxx",
  "status": "stopped",
  "message": "세션이 종료되었습니다.",
  "segments_count": 5
}
```

### 4. 활성 세션 목록

**`GET /asr/sessions`**

모든 활성 세션을 조회합니다.

**응답:**

```json
{
  "total": 2,
  "sessions": [
    {
      "session_id": "uuid-1",
      "device_id": "cores3_01",
      "is_active": true,
      ...
    }
  ]
}
```

---

## 🔌 WebSocket 프로토콜

### 연결

**URL:** `ws://localhost:8001/ws/asr/{session_id}`

### 클라이언트 → 서버 (오디오 전송)

```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_pcm_audio_int16",
  "timestamp": 1234567890
}
```

**오디오 형식:**

- 샘플레이트: 16000 Hz
- 비트 깊이: 16-bit PCM
- 채널: 모노
- 인코딩: Base64

### 서버 → 클라이언트 (인식 결과)

#### 1. 연결 확인

```json
{
  "type": "connected",
  "session_id": "uuid-xxxx",
  "message": "WebSocket 연결 성공. 오디오 전송을 시작하세요."
}
```

#### 2. 인식 결과

```json
{
  "type": "recognition_result",
  "session_id": "uuid-xxxx",
  "text": "안녕하세요",
  "timestamp": "2025-12-08 10:30:45",
  "duration": 2.3,
  "is_final": true,
  "is_emergency": false,
  "emergency_keywords": []
}
```

#### 3. 처리 중

```json
{
  "type": "processing",
  "session_id": "uuid-xxxx",
  "message": "음성 감지 중..."
}
```

#### 4. 에러

```json
{
  "type": "error",
  "session_id": "uuid-xxxx",
  "message": "오류 메시지"
}
```

#### 5. Ping-Pong (연결 유지)

**클라이언트 → 서버:**

```json
{
  "type": "ping"
}
```

**서버 → 클라이언트:**

```json
{
  "type": "pong",
  "session_id": "uuid-xxxx"
}
```

---

## 💻 사용 예제

### 1. Python 클라이언트

```python
import asyncio
import websockets
import json
import base64
import numpy as np

async def send_audio():
    # 1. 세션 시작
    session_response = requests.post('http://localhost:8001/asr/session/start',
                                     json={"device_id": "test_device"})
    session = session_response.json()
    ws_url = session['ws_url']

    # 2. WebSocket 연결
    async with websockets.connect(ws_url) as websocket:
        # 3. 오디오 전송
        audio_int16 = np.random.randint(-32768, 32767, size=1024, dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        message = {
            "type": "audio_chunk",
            "data": audio_base64,
            "timestamp": 0
        }

        await websocket.send(json.dumps(message))

        # 4. 결과 수신
        response = await websocket.recv()
        result = json.loads(response)
        print(f"인식 결과: {result}")

asyncio.run(send_audio())
```

### 2. 테스트 클라이언트 사용

```bash
# 오디오 파일로 테스트
python test_websocket_client.py --audio test.wav

# 옵션 지정
python test_websocket_client.py \
  --audio test.wav \
  --api-url http://localhost:8001 \
  --device-id cores3_01 \
  --chunk-size 1024
```

### 3. JavaScript/TypeScript (브라우저)

```typescript
const startASRSession = async () => {
  // 1. 세션 시작
  const response = await fetch("http://localhost:8001/asr/session/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: "web_client",
      language: "auto",
      sample_rate: 16000,
      vad_enabled: true,
    }),
  });

  const session = await response.json();

  // 2. WebSocket 연결
  const ws = new WebSocket(session.ws_url);

  ws.onopen = () => {
    console.log("WebSocket 연결됨");
  };

  ws.onmessage = (event) => {
    const result = JSON.parse(event.data);

    if (result.type === "recognition_result") {
      console.log("인식 결과:", result.text);
    }
  };

  // 3. 오디오 전송 (예: MediaRecorder로부터)
  const sendAudioChunk = (audioData: Int16Array) => {
    const base64 = btoa(
      String.fromCharCode(...new Uint8Array(audioData.buffer))
    );

    ws.send(
      JSON.stringify({
        type: "audio_chunk",
        data: base64,
        timestamp: Date.now(),
      })
    );
  };
};
```

### 4. ESP32 (Arduino)

```cpp
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>
#include <base64.h>

using namespace websockets;

WebsocketsClient ws;

void setup() {
  // 1. 세션 시작 (HTTP POST)
  String sessionId = requestASRSession();

  // 2. WebSocket 연결
  String wsUrl = "ws://192.168.1.100:8001/ws/asr/" + sessionId;
  ws.connect(wsUrl);

  // 3. 메시지 콜백 설정
  ws.onMessage([](WebsocketsMessage message) {
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, message.data());

    if (doc["type"] == "recognition_result") {
      String text = doc["text"];
      Serial.println("인식 결과: " + text);
      displayShowText(text.c_str());
    }
  });
}

void loop() {
  // 4. I2S 오디오 읽기
  int16_t audioBuffer[1024];
  size_t bytesRead;
  i2s_read(I2S_PORT_IN, audioBuffer, 2048, &bytesRead, portMAX_DELAY);

  // 5. Base64 인코딩
  String base64Audio = base64::encode((uint8_t*)audioBuffer, bytesRead);

  // 6. WebSocket 전송
  DynamicJsonDocument doc(2048);
  doc["type"] = "audio_chunk";
  doc["data"] = base64Audio;
  doc["timestamp"] = millis() / 1000;

  String json;
  serializeJson(doc, json);
  ws.send(json);

  ws.poll();
}
```

---

## 🔧 문제 해결

### 1. 모델 로딩 실패

**증상:**

```
❌ 모델 로딩 실패: [Errno 2] No such file or directory
```

**해결:**

- `models/` 디렉토리 경로 확인
- `demo_vad_final.py`의 `MODEL_DIR` 확인

### 2. WebSocket 연결 실패

**증상:**

```
🔌 WebSocket 연결 끊김: uuid-xxxx
```

**해결:**

- 방화벽 설정 확인 (포트 8001)
- 네트워크 연결 확인
- 클라이언트 타임아웃 설정 증가

### 3. 인식 결과 없음

**증상:**

- 오디오를 전송하지만 인식 결과가 없음

**해결:**

- 오디오 형식 확인 (16kHz, 16-bit PCM, 모노)
- VAD 임계값 조정 (`VADStreamingProcessor.energy_threshold`)
- 오디오 볼륨 확인 (너무 작으면 VAD가 감지 못함)

### 4. Base64 디코딩 오류

**증상:**

```
❌ base64 디코딩 오류
```

**해결:**

- Base64 문자열 형식 확인
- 패딩 확인 (=)
- UTF-8 인코딩 확인

---

## 📊 성능 최적화

### RK3588 NPU 활용

```bash
# 4개 코어 모두 사용
taskset 0x0F python asr_api_server.py

# 특정 코어 지정
taskset 0x03 python asr_api_server.py  # 코어 0,1 사용
```

### 동시 세션 제한

```python
# asr_api_server.py에서 최대 세션 수 제한
MAX_SESSIONS = 10

@app.post("/asr/session/start")
async def start_session(request: SessionStartRequest):
    if len(session_manager.sessions) >= MAX_SESSIONS:
        raise HTTPException(
            status_code=429,
            detail="최대 세션 수에 도달했습니다."
        )
    ...
```

---

## 📝 로그

### 로그 레벨 설정

```python
# asr_api_server.py
logging.basicConfig(level=logging.DEBUG)  # 디버그 모드
```

### 로그 위치

- 콘솔 출력: 실시간 로그
- 파일 저장: (선택적으로 구현 필요)

---

## 🔒 보안

### 인증 (선택적)

```python
# JWT 토큰 기반 인증 추가 예정
# Header: Authorization: Bearer <token>
```

### HTTPS/WSS

```python
# SSL 인증서 사용
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,
    ssl_keyfile="server.key",
    ssl_certfile="server.crt"
)
```

---

## 📞 지원

- **Issues**: GitHub Issues
- **Email**: support@example.com
- **문서**: [API 문서](http://localhost:8001/docs)

---

## 📄 라이선스

MIT License

---

**Powered by Sherpa-ONNX + FastAPI | RK3588 NPU Optimized**
