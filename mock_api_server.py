#!/usr/bin/env python3
"""
Mock API 서버

응급 알림 API를 시뮬레이션하는 테스트용 서버입니다.

실행 방법:
    python mock_api_server.py

엔드포인트:
    POST /api/emergency/quick
    POST /api/emergency/quick/<watch_id>
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# 수신 이벤트 저장 (메모리)
received_events = []


@app.route('/api/emergency/quick', methods=['POST'])
@app.route('/api/emergency/quick/<watch_id>', methods=['POST'])
def emergency_alert(watch_id=None):
    """
    응급 알림 수신 엔드포인트
    
    Args:
        watch_id: Watch ID (URL 파라미터, 선택적)
    """
    print("\n" + "=" * 80)
    print("🚨 응급 알림 수신!")
    print("=" * 80)
    
    event_data = {}
    
    # Watch ID (URL 파라미터)
    if watch_id:
        print(f"\n📍 Watch ID: {watch_id}")
        event_data['watch_id_from_url'] = watch_id
    
    # JSON 데이터
    if request.is_json:
        data = request.get_json()
        event_data.update(data)
        
        print(f"\n📦 JSON 데이터:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Form 데이터 (multipart/form-data)
    if request.form:
        print(f"\n📝 Form 데이터:")
        for key, value in request.form.items():
            event_data[key] = value
            print(f"   {key}: {value}")
    
    # 파일 데이터
    if request.files:
        print(f"\n📷 파일 데이터:")
        for key, file in request.files.items():
            print(f"   {key}: {file.filename} ({len(file.read())} bytes)")
            file.seek(0)  # 파일 포인터 리셋
            event_data[f'{key}_filename'] = file.filename
    
    # 헤더 정보
    print(f"\n📋 요청 정보:")
    print(f"   Content-Type: {request.content_type}")
    print(f"   Method: {request.method}")
    print(f"   Remote Addr: {request.remote_addr}")
    
    # 이벤트 저장
    event_record = {
        'timestamp': datetime.now().isoformat(),
        'data': event_data,
        'content_type': request.content_type,
    }
    received_events.append(event_record)
    
    print(f"\n💾 총 {len(received_events)}개의 이벤트 수신됨")
    print("=" * 80 + "\n")
    
    # 응답
    response = {
        'status': 'success',
        'message': 'Emergency alert received',
        'eventId': event_data.get('eventId', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'received_count': len(received_events),
    }
    
    return jsonify(response), 200


@app.route('/api/events', methods=['GET'])
def list_events():
    """
    수신한 이벤트 목록 조회
    """
    return jsonify({
        'total': len(received_events),
        'events': received_events
    }), 200


@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    """
    수신한 이벤트 목록 초기화
    """
    global received_events
    count = len(received_events)
    received_events = []
    
    return jsonify({
        'status': 'success',
        'message': f'Cleared {count} events'
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    서버 상태 확인
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'received_events': len(received_events),
    }), 200


@app.route('/', methods=['GET'])
def index():
    """
    루트 페이지
    """
    return """
    <html>
    <head>
        <title>Mock API Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            pre { background: #f4f4f4; padding: 10px; border-radius: 5px; }
            .endpoint { background: #e8f4f8; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }
        </style>
    </head>
    <body>
        <h1>🚀 Mock API Server</h1>
        <p>응급 알림 API를 시뮬레이션하는 테스트용 서버입니다.</p>
        
        <h2>📍 사용 가능한 엔드포인트</h2>
        
        <div class="endpoint">
            <h3>POST /api/emergency/quick</h3>
            <p>응급 알림 수신 (JSON 또는 Multipart)</p>
            <pre>curl -X POST http://localhost:10008/api/emergency/quick \
  -H "Content-Type: application/json" \
  -d '{"eventId": "test123", "note": "응급 호출 발생"}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>POST /api/emergency/quick/{watch_id}</h3>
            <p>응급 알림 수신 (Watch ID 포함)</p>
            <pre>curl -X POST http://localhost:10008/api/emergency/quick/watch_123 \
  -H "Content-Type: application/json" \
  -d '{"eventId": "test123", "note": "응급 호출 발생"}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>GET /api/events</h3>
            <p>수신한 이벤트 목록 조회</p>
            <pre>curl http://localhost:10008/api/events</pre>
        </div>
        
        <div class="endpoint">
            <h3>POST /api/events/clear</h3>
            <p>수신한 이벤트 목록 초기화</p>
            <pre>curl -X POST http://localhost:10008/api/events/clear</pre>
        </div>
        
        <div class="endpoint">
            <h3>GET /health</h3>
            <p>서버 상태 확인</p>
            <pre>curl http://localhost:10008/health</pre>
        </div>
        
        <h2>📊 현재 상태</h2>
        <p>수신한 이벤트: <strong>{}</strong>개</p>
        <p>서버 시간: <strong>{}</strong></p>
    </body>
    </html>
    """.format(len(received_events), datetime.now().isoformat())


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("  🚀 Mock API 서버 시작")
    print("=" * 80)
    print("\n📍 서버 정보:")
    print("   - 주소: http://0.0.0.0:10008")
    print("   - 웹 UI: http://localhost:10008")
    print("   - 응급 알림 엔드포인트: /api/emergency/quick")
    print("   - 이벤트 목록: /api/events")
    print("   - 상태 확인: /health")
    print("\n💡 사용 방법:")
    print("   1. 이 서버를 실행한 상태로 유지")
    print("   2. 다른 터미널에서 테스트 스크립트 실행")
    print("      python test_integration.py")
    print("   3. 또는 demo_vad_final.py에서 API 엔드포인트 설정")
    print("      http://localhost:10008/api/emergency/quick")
    print("\n" + "=" * 80 + "\n")
    
    try:
        app.run(
            host='0.0.0.0',
            port=10008,
            debug=True,
            use_reloader=False  # 리로더 비활성화 (중복 실행 방지)
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  서버 종료")
        print(f"📊 총 {len(received_events)}개의 이벤트를 수신했습니다.\n")
