"""
API 엔드포인트 관리 UI (Gradio 탭)

주요 기능:
- 엔드포인트 목록 조회
- 엔드포인트 추가/수정/삭제
- 엔드포인트 활성화/비활성화
- 엔드포인트 테스트
- watch_id / sender_id 설정
"""

import gradio as gr
import logging
from typing import List, Any

from emergency_alert_manager import get_emergency_manager

logger = logging.getLogger(__name__)


def format_endpoints_table(endpoints: List[dict]) -> str:
    """
    엔드포인트 목록을 테이블 형식 문자열로 변환
    
    Args:
        endpoints: 엔드포인트 목록
        
    Returns:
        str: 테이블 형식 문자열
    """
    if not endpoints:
        return "등록된 엔드포인트가 없습니다."
    
    table = "=" * 100 + "\n"
    table += f"{'ID':<5} {'이름':<20} {'URL':<40} {'상태':<8} {'타입':<10}\n"
    table += "=" * 100 + "\n"
    
    for ep in endpoints:
        ep_id = ep["id"]
        name = ep["name"][:18]
        url = ep["url"][:38]
        enabled = "활성화" if ep["enabled"] else "비활성화"
        ep_type = ep["type"]
        
        table += f"{ep_id:<5} {name:<20} {url:<40} {enabled:<8} {ep_type:<10}\n"
    
    table += "=" * 100
    return table


# ==================
# 엔드포인트 관리 핸들러
# ==================

def list_endpoints_handler():
    """엔드포인트 목록 조회"""
    try:
        manager = get_emergency_manager()
        endpoints = manager.list_endpoints()
        
        table = format_endpoints_table(endpoints)
        status = f"✅ 총 {len(endpoints)}개의 엔드포인트가 등록되어 있습니다."
        
        return table, status
    except Exception as e:
        logger.error(f"엔드포인트 목록 조회 오류: {e}", exc_info=True)
        return "❌ 오류 발생", f"오류: {str(e)}"


def add_endpoint_handler(name: str, url: str, endpoint_type: str, enabled: bool):
    """엔드포인트 추가"""
    try:
        if not name or not url:
            return "❌ 이름과 URL을 모두 입력해주세요.", "⚠️ 입력 오류"
        
        manager = get_emergency_manager()
        endpoint_id = manager.add_endpoint(
            name=name,
            url=url,
            method="POST",
            endpoint_type=endpoint_type.lower(),
            enabled=enabled
        )
        
        # 목록 새로고침
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        status = f"✅ 엔드포인트 추가 완료 (ID: {endpoint_id})"
        
        return table, status
    except Exception as e:
        logger.error(f"엔드포인트 추가 오류: {e}", exc_info=True)
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        return table, f"❌ 추가 실패: {str(e)}"


def delete_endpoint_handler(endpoint_id: int):
    """엔드포인트 삭제"""
    try:
        if endpoint_id <= 0:
            return "❌ 올바른 ID를 입력해주세요.", "⚠️ 입력 오류"
        
        manager = get_emergency_manager()
        manager.delete_endpoint(endpoint_id)
        
        # 목록 새로고침
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        status = f"✅ 엔드포인트 삭제 완료 (ID: {endpoint_id})"
        
        return table, status
    except Exception as e:
        logger.error(f"엔드포인트 삭제 오류: {e}", exc_info=True)
        manager = get_emergency_manager()
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        return table, f"❌ 삭제 실패: {str(e)}"


def toggle_endpoint_handler(endpoint_id: int, enabled: bool):
    """엔드포인트 활성화/비활성화"""
    try:
        if endpoint_id <= 0:
            return "❌ 올바른 ID를 입력해주세요.", "⚠️ 입력 오류"
        
        manager = get_emergency_manager()
        manager.update_endpoint(endpoint_id, enabled=enabled)
        
        # 목록 새로고침
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        status_text = "활성화" if enabled else "비활성화"
        status = f"✅ 엔드포인트 {status_text} 완료 (ID: {endpoint_id})"
        
        return table, status
    except Exception as e:
        logger.error(f"엔드포인트 토글 오류: {e}", exc_info=True)
        manager = get_emergency_manager()
        endpoints = manager.list_endpoints()
        table = format_endpoints_table(endpoints)
        return table, f"❌ 상태 변경 실패: {str(e)}"


def test_endpoint_handler(endpoint_id: int):
    """엔드포인트 테스트"""
    try:
        if endpoint_id <= 0:
            return "⚠️ 올바른 ID를 입력해주세요."
        
        manager = get_emergency_manager()
        result = manager.test_endpoint(endpoint_id, timeout=10)
        
        if result.get("success"):
            status = f"✅ 테스트 성공 (ID: {endpoint_id})\n\n"
            status += f"HTTP 상태 코드: {result.get('status_code')}\n"
            status += f"응답 시간: {result.get('timestamp')}\n"
            if result.get('response_text'):
                status += f"응답 내용: {result.get('response_text')[:200]}"
        else:
            status = f"❌ 테스트 실패 (ID: {endpoint_id})\n\n"
            status += f"오류: {result.get('error')}\n"
            if result.get('response_text'):
                status += f"응답 내용: {result.get('response_text')[:200]}"
        
        return status
    except Exception as e:
        logger.error(f"엔드포인트 테스트 오류: {e}", exc_info=True)
        return f"❌ 테스트 실패: {str(e)}"


# ==================
# 설정 관리 핸들러
# ==================

def get_settings_handler():
    """현재 설정 조회"""
    try:
        manager = get_emergency_manager()
        watch_id = manager.get_watch_id()
        sender_id = manager.get_sender_id()
        
        return watch_id, sender_id, "✅ 설정 로드 완료"
    except Exception as e:
        logger.error(f"설정 조회 오류: {e}", exc_info=True)
        return "", "", f"❌ 오류: {str(e)}"


def save_settings_handler(watch_id: str, sender_id: str):
    """설정 저장"""
    try:
        if not watch_id or not sender_id:
            return "⚠️ 모든 필드를 입력해주세요."
        
        manager = get_emergency_manager()
        manager.set_watch_id(watch_id)
        manager.set_sender_id(sender_id)
        
        return f"✅ 설정 저장 완료\n\nWatch ID: {watch_id}\nSender ID: {sender_id}"
    except Exception as e:
        logger.error(f"설정 저장 오류: {e}", exc_info=True)
        return f"❌ 저장 실패: {str(e)}"


# ==================
# UI 생성
# ==================

def create_api_management_tab():
    """API 엔드포인트 관리 탭 생성"""
    
    with gr.Tab("⚙️ API 엔드포인트 관리"):
        gr.Markdown("""
        ### API 엔드포인트 관리
        
        응급 상황 발생 시 알림을 전송할 API 엔드포인트를 관리합니다.
        
        **주요 기능:**
        - ✅ 엔드포인트 추가/수정/삭제
        - ✅ 엔드포인트 활성화/비활성화
        - ✅ 엔드포인트 연결 테스트
        - ✅ Watch ID / Sender ID 설정
        """)
        
        # ==================
        # 섹션 1: 엔드포인트 목록
        # ==================
        gr.Markdown("### 📋 엔드포인트 목록")
        
        with gr.Row():
            endpoint_list = gr.Textbox(
                label="등록된 엔드포인트",
                lines=12,
                max_lines=20,
                interactive=False,
                show_copy_button=True,
            )
        
        with gr.Row():
            refresh_btn = gr.Button("🔄 목록 새로고침", variant="secondary", size="sm")
        
        endpoint_status = gr.Textbox(label="상태", lines=2)
        
        # ==================
        # 섹션 2: 엔드포인트 추가
        # ==================
        gr.Markdown("### ➕ 새 엔드포인트 추가")
        
        with gr.Row():
            with gr.Column(scale=2):
                new_name = gr.Textbox(
                    label="이름",
                    placeholder="예: Main API Server",
                )
            with gr.Column(scale=3):
                new_url = gr.Textbox(
                    label="URL",
                    placeholder="예: http://10.10.11.23:10008/api/emergency/quick",
                )
        
        with gr.Row():
            with gr.Column():
                new_type = gr.Dropdown(
                    choices=["JSON", "Multipart"],
                    value="JSON",
                    label="전송 타입",
                )
            with gr.Column():
                new_enabled = gr.Checkbox(
                    label="활성화",
                    value=True,
                )
        
        with gr.Row():
            add_btn = gr.Button("➕ 추가", variant="primary", size="lg")
        
        # ==================
        # 섹션 3: 엔드포인트 관리
        # ==================
        gr.Markdown("### 🔧 엔드포인트 관리")
        
        with gr.Row():
            with gr.Column():
                manage_id = gr.Number(
                    label="엔드포인트 ID",
                    value=1,
                    precision=0,
                )
            with gr.Column():
                gr.Markdown("**작업 선택:**")
        
        with gr.Row():
            delete_btn = gr.Button("🗑️ 삭제", variant="stop", size="sm")
            enable_btn = gr.Button("✅ 활성화", variant="secondary", size="sm")
            disable_btn = gr.Button("❌ 비활성화", variant="secondary", size="sm")
            test_btn = gr.Button("🧪 테스트", variant="primary", size="sm")
        
        test_status = gr.Textbox(label="테스트 결과", lines=5)
        
        # ==================
        # 섹션 4: 설정 관리
        # ==================
        gr.Markdown("### ⚙️ 전역 설정")
        
        with gr.Row():
            with gr.Column():
                watch_id_input = gr.Textbox(
                    label="Watch ID",
                    placeholder="예: watch_1760663070591_8022",
                )
            with gr.Column():
                sender_id_input = gr.Textbox(
                    label="Sender ID",
                    placeholder="예: voice_asr_system",
                )
        
        with gr.Row():
            load_settings_btn = gr.Button("📥 설정 불러오기", variant="secondary", size="sm")
            save_settings_btn = gr.Button("💾 설정 저장", variant="primary", size="lg")
        
        settings_status = gr.Textbox(label="설정 상태", lines=3)
        
        # ==================
        # 사용 방법 안내
        # ==================
        gr.Markdown("""
        ### 📖 사용 방법
        
        #### 1. 엔드포인트 추가
        1. "새 엔드포인트 추가" 섹션에서 이름과 URL 입력
        2. 전송 타입 선택 (JSON 또는 Multipart)
        3. "추가" 버튼 클릭
        
        #### 2. 엔드포인트 관리
        1. 목록에서 관리할 엔드포인트의 ID 확인
        2. "엔드포인트 ID" 입력
        3. 원하는 작업 버튼 클릭 (삭제/활성화/비활성화/테스트)
        
        #### 3. 설정 관리
        1. "설정 불러오기"로 현재 설정 확인
        2. Watch ID와 Sender ID 수정
        3. "설정 저장" 클릭
        
        #### 💡 참고사항
        - 응급 상황 발생 시 **활성화된 엔드포인트로만 전송**됩니다.
        - 비활성화된 엔드포인트는 전송 대상에서 제외됩니다.
        - 테스트 기능으로 연결을 미리 확인하세요.
        """)
        
        # ==================
        # 이벤트 핸들러 연결
        # ==================
        
        # 초기 로드
        refresh_btn.click(
            fn=list_endpoints_handler,
            inputs=None,
            outputs=[endpoint_list, endpoint_status],
        )
        
        # 추가
        add_btn.click(
            fn=add_endpoint_handler,
            inputs=[new_name, new_url, new_type, new_enabled],
            outputs=[endpoint_list, endpoint_status],
        )
        
        # 삭제
        delete_btn.click(
            fn=delete_endpoint_handler,
            inputs=[manage_id],
            outputs=[endpoint_list, endpoint_status],
        )
        
        # 활성화
        enable_btn.click(
            fn=lambda eid: toggle_endpoint_handler(eid, True),
            inputs=[manage_id],
            outputs=[endpoint_list, endpoint_status],
        )
        
        # 비활성화
        disable_btn.click(
            fn=lambda eid: toggle_endpoint_handler(eid, False),
            inputs=[manage_id],
            outputs=[endpoint_list, endpoint_status],
        )
        
        # 테스트
        test_btn.click(
            fn=test_endpoint_handler,
            inputs=[manage_id],
            outputs=[test_status],
        )
        
        # 설정 불러오기
        load_settings_btn.click(
            fn=get_settings_handler,
            inputs=None,
            outputs=[watch_id_input, sender_id_input, settings_status],
        )
        
        # 설정 저장
        save_settings_btn.click(
            fn=save_settings_handler,
            inputs=[watch_id_input, sender_id_input],
            outputs=[settings_status],
        )


if __name__ == "__main__":
    # 테스트용 단독 실행
    import gradio as gr
    
    with gr.Blocks() as demo:
        create_api_management_tab()
    
    demo.launch()
