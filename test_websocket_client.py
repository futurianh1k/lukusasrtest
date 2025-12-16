# -*- coding: utf-8 -*-
"""
ASR WebSocket 클라이언트 테스트 스크립트

사용법:
    python test_websocket_client.py --audio test.wav
"""

import asyncio
import json
import base64
import argparse
import numpy as np
import soundfile as sf
import websockets
import requests
from pathlib import Path


class ASRWebSocketClient:
    """ASR WebSocket 클라이언트"""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.session_id = None
        self.ws_url = None
    
    def start_session(self, device_id: str = "test_device") -> dict:
        """세션 시작"""
        url = f"{self.api_url}/asr/session/start"
        
        data = {
            "device_id": device_id,
            "language": "auto",
            "sample_rate": 16000,
            "vad_enabled": True
        }
        
        print(f"📤 세션 시작 요청: {url}")
        print(f"   데이터: {data}")
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        self.session_id = result['session_id']
        self.ws_url = result['ws_url']
        
        print(f"✅ 세션 생성 완료:")
        print(f"   - Session ID: {self.session_id}")
        print(f"   - WebSocket URL: {self.ws_url}")
        
        return result
    
    async def send_audio_file(self, audio_path: str, chunk_size: int = 1024):
        """
        오디오 파일을 WebSocket으로 전송
        
        Args:
            audio_path: 오디오 파일 경로
            chunk_size: 청크 크기 (samples)
        """
        # 오디오 파일 읽기
        audio, sr = sf.read(audio_path, dtype='float32')
        
        print(f"\n🎵 오디오 파일 로드:")
        print(f"   - 파일: {audio_path}")
        print(f"   - 샘플레이트: {sr} Hz")
        print(f"   - 길이: {len(audio)} samples ({len(audio)/sr:.2f}초)")
        print(f"   - 채널: {audio.shape}")
        
        # 스테레오 → 모노
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
            print("   - 스테레오 → 모노 변환")
        
        # 16kHz 리샘플링 (필요시)
        if sr != 16000:
            print(f"   ⚠️ 리샘플링 필요: {sr}Hz → 16000Hz")
            print("   💡 librosa 또는 resampy 사용 권장")
            # 여기서는 간단히 진행
        
        # WebSocket 연결
        print(f"\n🔗 WebSocket 연결 시도: {self.ws_url}")
        
        async with websockets.connect(self.ws_url) as websocket:
            print("✅ WebSocket 연결 성공!")
            
            # 연결 확인 메시지 수신
            welcome_msg = await websocket.recv()
            print(f"📨 서버 메시지: {welcome_msg}")
            
            # 오디오를 청크로 나누어 전송
            total_chunks = len(audio) // chunk_size + (1 if len(audio) % chunk_size else 0)
            
            print(f"\n📡 오디오 전송 시작 (총 {total_chunks}개 청크)...")
            
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i:i+chunk_size]
                
                # float32 → int16
                chunk_int16 = (chunk * 32768).astype(np.int16)
                
                # int16 → bytes → base64
                chunk_bytes = chunk_int16.tobytes()
                chunk_base64 = base64.b64encode(chunk_bytes).decode('utf-8')
                
                # JSON 메시지 생성
                message = {
                    "type": "audio_chunk",
                    "data": chunk_base64,
                    "timestamp": i / sr
                }
                
                # 전송
                await websocket.send(json.dumps(message))
                
                # 진행률 표시
                progress = (i // chunk_size + 1) / total_chunks * 100
                print(f"\r   진행률: {progress:.1f}% ({i//chunk_size + 1}/{total_chunks})", end='', flush=True)
                
                # 실시간 재생 시뮬레이션 (선택적)
                await asyncio.sleep(chunk_size / 16000)
                
                # 서버 응답 확인 (논블로킹)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                    result = json.loads(response)
                    
                    if result.get('type') == 'recognition_result':
                        print(f"\n✅ 인식 결과:")
                        print(f"   - 텍스트: {result['text']}")
                        print(f"   - 타임스탬프: {result['timestamp']}")
                        print(f"   - 길이: {result['duration']:.2f}초")
                        if result.get('is_emergency'):
                            print(f"   🚨 응급 상황: {result['emergency_keywords']}")
                    
                    elif result.get('type') == 'processing':
                        print(f"\n🗣️ {result['message']}")
                
                except asyncio.TimeoutError:
                    pass  # 응답 없음
            
            print("\n\n📤 전송 완료! 최종 결과 대기 중...")
            
            # 최종 결과 대기 (최대 5초)
            try:
                for _ in range(50):  # 5초 동안 대기
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    result = json.loads(response)
                    
                    if result.get('type') == 'recognition_result':
                        print(f"\n✅ 최종 인식 결과:")
                        print(f"   - 텍스트: {result['text']}")
                        print(f"   - 타임스탬프: {result['timestamp']}")
                        print(f"   - 길이: {result['duration']:.2f}초")
                        if result.get('is_emergency'):
                            print(f"   🚨 응급 상황: {result['emergency_keywords']}")
                        break
            
            except asyncio.TimeoutError:
                print("⏱️ 타임아웃 - 더 이상 결과가 없습니다.")
    
    def stop_session(self):
        """세션 종료"""
        if not self.session_id:
            print("⚠️ 활성 세션이 없습니다.")
            return
        
        url = f"{self.api_url}/asr/session/{self.session_id}/stop"
        
        print(f"\n🛑 세션 종료 요청: {url}")
        
        response = requests.post(url)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ 세션 종료:")
        print(f"   - Session ID: {result['session_id']}")
        print(f"   - 상태: {result['status']}")
        print(f"   - 인식 세그먼트: {result['segments_count']}개")
    
    def get_session_status(self):
        """세션 상태 조회"""
        if not self.session_id:
            print("⚠️ 활성 세션이 없습니다.")
            return
        
        url = f"{self.api_url}/asr/session/{self.session_id}/status"
        
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n📊 세션 상태:")
        print(f"   - Session ID: {result['session_id']}")
        print(f"   - Device ID: {result['device_id']}")
        print(f"   - 활성: {result['is_active']}")
        print(f"   - 처리 중: {result['is_processing']}")
        print(f"   - 세그먼트: {result['segments_count']}개")
        print(f"   - 마지막 결과: {result['last_result']}")
        
        return result


async def main():
    parser = argparse.ArgumentParser(description="ASR WebSocket 클라이언트 테스트")
    parser.add_argument("--audio", type=str, required=True, help="테스트 오디오 파일 경로")
    parser.add_argument("--api-url", type=str, default="http://localhost:8001", help="API 서버 URL")
    parser.add_argument("--device-id", type=str, default="test_device", help="장비 ID")
    parser.add_argument("--chunk-size", type=int, default=1024, help="오디오 청크 크기")
    
    args = parser.parse_args()
    
    # 오디오 파일 확인
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"❌ 오디오 파일을 찾을 수 없습니다: {audio_path}")
        return
    
    print("=" * 60)
    print("🎤 ASR WebSocket 클라이언트 테스트")
    print("=" * 60)
    
    client = ASRWebSocketClient(api_url=args.api_url)
    
    try:
        # 1. 세션 시작
        client.start_session(device_id=args.device_id)
        
        # 2. 오디오 전송
        await client.send_audio_file(str(audio_path), chunk_size=args.chunk_size)
        
        # 3. 세션 상태 확인
        client.get_session_status()
        
        # 4. 세션 종료
        client.stop_session()
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
