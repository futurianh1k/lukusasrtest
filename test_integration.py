#!/usr/bin/env python3
"""
API 엔드포인트 통합 테스트 스크립트

주요 기능:
- 엔드포인트 추가/조회/삭제 테스트
- 설정 저장/조회 테스트  
- 응급 알림 전송 테스트
- Mock 서버 실행 가이드
"""

import sys
import json
from datetime import datetime

from emergency_alert_manager import EmergencyAlertManager


def print_section(title: str):
    """섹션 제목 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_endpoint_management():
    """엔드포인트 관리 테스트"""
    print_section("1. 엔드포인트 관리 테스트")
    
    # 매니저 초기화
    manager = EmergencyAlertManager(db_path="./test_data/api_endpoints_test.db")
    
    # 1-1. 엔드포인트 추가
    print("📝 엔드포인트 추가 테스트")
    endpoint_id_1 = manager.add_endpoint(
        name="Main API Server",
        url="http://10.10.11.23:10008/api/emergency/quick",
        endpoint_type="json",
        enabled=True
    )
    print(f"   ✅ Main API Server 추가됨 (ID: {endpoint_id_1})")
    
    endpoint_id_2 = manager.add_endpoint(
        name="Backup API Server",
        url="http://10.10.11.24:10008/api/emergency/quick",
        endpoint_type="json",
        enabled=False
    )
    print(f"   ✅ Backup API Server 추가됨 (ID: {endpoint_id_2})")
    
    # 1-2. 엔드포인트 목록 조회
    print("\n📋 엔드포인트 목록 조회")
    endpoints = manager.list_endpoints()
    for ep in endpoints:
        status = "활성화" if ep["enabled"] else "비활성화"
        print(f"   [ID {ep['id']}] {ep['name']}: {ep['url']} ({status})")
    
    # 1-3. 엔드포인트 수정
    print("\n✏️ 엔드포인트 수정 테스트")
    manager.update_endpoint(endpoint_id_2, enabled=True)
    print(f"   ✅ Backup API Server 활성화됨 (ID: {endpoint_id_2})")
    
    # 1-4. 활성화된 엔드포인트만 조회
    print("\n📋 활성화된 엔드포인트만 조회")
    active_endpoints = manager.get_enabled_endpoints()
    for ep in active_endpoints:
        print(f"   [ID {ep['id']}] {ep['name']}: {ep['url']}")
    
    print("\n✅ 엔드포인트 관리 테스트 완료")
    return manager


def test_settings():
    """설정 관리 테스트"""
    print_section("2. 설정 관리 테스트")
    
    manager = EmergencyAlertManager(db_path="./test_data/api_endpoints_test.db")
    
    # 2-1. 설정 저장
    print("💾 설정 저장 테스트")
    manager.set_watch_id("watch_test_12345")
    manager.set_sender_id("test_asr_system")
    print("   ✅ Watch ID 저장: watch_test_12345")
    print("   ✅ Sender ID 저장: test_asr_system")
    
    # 2-2. 설정 조회
    print("\n📥 설정 조회 테스트")
    watch_id = manager.get_watch_id()
    sender_id = manager.get_sender_id()
    print(f"   Watch ID: {watch_id}")
    print(f"   Sender ID: {sender_id}")
    
    print("\n✅ 설정 관리 테스트 완료")


def test_emergency_alert():
    """응급 알림 전송 테스트"""
    print_section("3. 응급 알림 전송 테스트")
    
    manager = EmergencyAlertManager(db_path="./test_data/api_endpoints_test.db")
    
    # 3-1. 응급 알림 전송
    print("🚨 응급 알림 전송 테스트")
    print("   주의: 실제 서버가 실행 중이 아니면 연결 오류가 발생합니다.\n")
    
    result = manager.send_emergency_alert(
        recognized_text="도와줘 사람이 쓰러졌어",
        emergency_keywords=["도와줘", "쓰러졌어"],
        timeout=5,
        retry_count=2,
    )
    
    print(f"\n📊 전송 결과:")
    print(f"   성공 여부: {result['success']}")
    print(f"   대상 엔드포인트: {result['total_endpoints']}개")
    print(f"   성공: {result['success_count']}개")
    print(f"   실패: {result['failed_count']}개")
    print(f"   이벤트 ID: {result['event_id']}")
    
    print("\n📝 상세 결과:")
    for r in result['results']:
        name = r['endpoint_name']
        success = r['result']['success']
        status = "✅ 성공" if success else "❌ 실패"
        error = r['result'].get('error', '')
        print(f"   [{name}] {status}")
        if error:
            print(f"      오류: {error}")
    
    print("\n✅ 응급 알림 전송 테스트 완료")


def test_endpoint_test():
    """엔드포인트 개별 테스트"""
    print_section("4. 엔드포인트 개별 테스트")
    
    manager = EmergencyAlertManager(db_path="./test_data/api_endpoints_test.db")
    
    endpoints = manager.list_endpoints()
    if not endpoints:
        print("⚠️ 테스트할 엔드포인트가 없습니다.")
        return
    
    # 첫 번째 엔드포인트 테스트
    endpoint = endpoints[0]
    print(f"🧪 엔드포인트 테스트: {endpoint['name']}")
    print(f"   URL: {endpoint['url']}\n")
    
    result = manager.test_endpoint(endpoint['id'], timeout=5)
    
    print(f"📊 테스트 결과:")
    print(f"   성공 여부: {result.get('success')}")
    print(f"   상태 코드: {result.get('status_code')}")
    print(f"   오류: {result.get('error', '없음')}")
    
    print("\n✅ 엔드포인트 테스트 완료")


def show_mock_server_guide():
    """Mock 서버 실행 가이드"""
    print_section("Mock 서버 실행 가이드")
    
    print("""
실제 서버가 없는 경우, 다음 Mock 서버를 사용하여 테스트할 수 있습니다:

1. Flask 설치:
   pip install flask

2. mock_server.py 파일 생성:

```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/api/emergency/quick', methods=['POST'])
@app.route('/api/emergency/quick/<watch_id>', methods=['POST'])
def emergency_alert(watch_id=None):
    print("\\n" + "=" * 60)
    print("🚨 응급 알림 수신!")
    print("=" * 60)
    
    # JSON 데이터
    if request.is_json:
        data = request.get_json()
        print(f"\\n📦 JSON 데이터:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Form 데이터
    if request.form:
        print(f"\\n📝 Form 데이터:")
        for key, value in request.form.items():
            print(f"   {key}: {value}")
    
    # 파일 데이터
    if request.files:
        print(f"\\n📷 파일 데이터:")
        for key, file in request.files.items():
            print(f"   {key}: {file.filename}")
    
    print("\\n" + "=" * 60 + "\\n")
    
    return jsonify({
        'status': 'success',
        'message': 'Emergency alert received',
        'timestamp': str(datetime.now())
    }), 200

if __name__ == '__main__':
    print("🚀 Mock API 서버 시작...")
    print("📍 주소: http://0.0.0.0:10008")
    print("📍 엔드포인트: /api/emergency/quick")
    print("\\n")
    app.run(host='0.0.0.0', port=10008, debug=True)
```

3. Mock 서버 실행:
   python mock_server.py

4. 다른 터미널에서 테스트 실행:
   python test_integration.py

5. Mock 서버 로그에서 수신된 데이터 확인
""")


def cleanup_test_db():
    """테스트 DB 정리"""
    import os
    import shutil
    
    test_dir = "./test_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"✅ 테스트 디렉토리 정리: {test_dir}")


def main():
    """메인 함수"""
    print("\n" + "=" * 80)
    print("  🧪 API 엔드포인트 통합 테스트")
    print("=" * 80)
    
    # 테스트 DB 초기화
    import os
    os.makedirs("./test_data", exist_ok=True)
    
    try:
        # 1. 엔드포인트 관리 테스트
        test_endpoint_management()
        
        # 2. 설정 관리 테스트
        test_settings()
        
        # 3. 응급 알림 전송 테스트
        test_emergency_alert()
        
        # 4. 엔드포인트 개별 테스트
        test_endpoint_test()
        
        # 5. Mock 서버 가이드
        show_mock_server_guide()
        
        print_section("✅ 모든 테스트 완료")
        print("\n💡 참고사항:")
        print("   - 실제 서버가 없으면 연결 오류가 발생하는 것이 정상입니다.")
        print("   - Mock 서버를 실행하여 실제 전송을 테스트해보세요.")
        print("   - 테스트 DB는 ./test_data/api_endpoints_test.db에 저장됩니다.")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    # 정리 여부 확인
    print("\n")
    cleanup = input("테스트 DB를 삭제하시겠습니까? (y/N): ").strip().lower()
    if cleanup == 'y':
        cleanup_test_db()
    else:
        print("테스트 DB가 유지됩니다: ./test_data/")


if __name__ == "__main__":
    main()
