# -*- coding: utf-8 -*-
"""
CSV 리포트 생성 모듈

음성인식 결과를 CSV 형식으로 리포트 생성
"""

import os
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def generate_mic_session_csv_report(
    sessions: List[Dict],
    matcher,  # SpeechRecognitionMatcher 객체
    output_csv_path: Optional[str] = None
) -> Optional[str]:
    """
    마이크 실시간 음성인식 세션 결과에 대한 CSV 리포트 생성

    Args:
        sessions: 세션 결과 리스트 (각 dict는 session_id, timestamp, duration, ground_truth, asr_result 포함)
        matcher: SpeechRecognitionMatcher 객체
        output_csv_path: 저장될 CSV 경로 (None이면 자동 생성)

    Returns:
        생성된 CSV 파일 경로 또는 None
    """
    if not sessions:
        logger.warning("⚠️ 생성할 세션 결과가 없습니다.")
        return None

    # 자동 파일명 생성
    if output_csv_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = f"mic_session_cer_report_{timestamp}.csv"

    rows = []

    for session in sessions:
        session_id = session.get("session_id", "N/A")
        timestamp = session.get("timestamp", "N/A")
        duration = session.get("duration", 0.0)
        gt = session.get("ground_truth", "")
        asr = session.get("asr_result", "")

        # CER 직접 계산
        cer_direct = matcher.cer_direct(asr, gt)

        # jiwer CER 계산
        cer_jiwer_data = matcher.cer_jiwer(asr, gt)

        row = {
            "session_id": session_id,
            "timestamp": timestamp,
            "duration_sec": f"{duration:.2f}",
            "ground_truth": gt,
            "asr": asr,
            # 직접 CER
            "cer_direct": f"{cer_direct['CER']:.4f}",
            "S_direct": cer_direct["S"],
            "D_direct": cer_direct["D"],
            "I_direct": cer_direct["I"],
            "N_direct": cer_direct["N"],
        }

        # jiwer CER 존재 여부 체크
        if cer_jiwer_data:
            row.update({
                "cer_jiwer": f"{cer_jiwer_data['CER']:.4f}",
                "S_jiwer": cer_jiwer_data["S"],
                "D_jiwer": cer_jiwer_data["D"],
                "I_jiwer": cer_jiwer_data["I"],
                "N_jiwer": cer_jiwer_data["N"],
            })
        else:
            row.update({
                "cer_jiwer": "",
                "S_jiwer": "",
                "D_jiwer": "",
                "I_jiwer": "",
                "N_jiwer": "",
            })

        rows.append(row)

    # CSV 저장
    header = [
        "session_id", "timestamp", "duration_sec", "ground_truth", "asr",
        "cer_direct", "S_direct", "D_direct", "I_direct", "N_direct",
        "cer_jiwer",  "S_jiwer", "D_jiwer", "I_jiwer", "N_jiwer"
    ]

    try:
        with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"[✔] 마이크 세션 CSV 리포트 생성 완료 → {output_csv_path}")
        return output_csv_path
    except Exception as e:
        logger.error(f"❌ CSV 리포트 생성 실패: {e}", exc_info=True)
        return None


def generate_batch_csv_report(
    file_names: List[str],
    ground_truths: List[str],
    asr_results: List[str],
    matcher,  # SpeechRecognitionMatcher 객체
    output_csv_path: Optional[str] = None
) -> Optional[str]:
    """
    배치 파일 음성 인식 결과에 대한 CSV 리포트 생성

    Args:
        file_names: 파일명 리스트
        ground_truths: 정답(GT) 리스트
        asr_results: ASR 인식 결과 리스트
        matcher: SpeechRecognitionMatcher 객체
        output_csv_path: 저장될 CSV 경로 (None이면 자동 생성)

    Returns:
        생성된 CSV 파일 경로 또는 None
    """
    if len(ground_truths) != len(asr_results):
        logger.error("❌ GT와 ASR 개수가 다릅니다.")
        return None

    if len(file_names) != len(ground_truths):
        # 길이가 다르면 자동 번호 생성
        file_names = [f"audio_{i+1}.wav" for i in range(len(ground_truths))]

    # 자동 파일명 생성
    if output_csv_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = f"batch_cer_report_{timestamp}.csv"

    rows = []

    for idx, (fname, gt, asr) in enumerate(zip(file_names, ground_truths, asr_results)):
        # CER 직접 계산
        cer_direct = matcher.cer_direct(asr, gt)

        # jiwer CER 계산
        cer_jiwer_data = matcher.cer_jiwer(asr, gt)

        row = {
            "file_name": fname,
            "ground_truth": gt,
            "asr": asr,
            # 직접 CER
            "cer_direct": f"{cer_direct['CER']:.4f}",
            "S_direct": cer_direct["S"],
            "D_direct": cer_direct["D"],
            "I_direct": cer_direct["I"],
            "N_direct": cer_direct["N"],
        }

        # jiwer CER 존재 여부 체크
        if cer_jiwer_data:
            row.update({
                "cer_jiwer": f"{cer_jiwer_data['CER']:.4f}",
                "S_jiwer": cer_jiwer_data["S"],
                "D_jiwer": cer_jiwer_data["D"],
                "I_jiwer": cer_jiwer_data["I"],
                "N_jiwer": cer_jiwer_data["N"],
            })
        else:
            row.update({
                "cer_jiwer": "",
                "S_jiwer": "",
                "D_jiwer": "",
                "I_jiwer": "",
                "N_jiwer": "",
            })

        rows.append(row)

    # CSV 저장
    header = [
        "file_name", "ground_truth", "asr",
        "cer_direct", "S_direct", "D_direct", "I_direct", "N_direct",
        "cer_jiwer",  "S_jiwer", "D_jiwer", "I_jiwer", "N_jiwer"
    ]

    try:
        with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"[✔] 배치 CSV 리포트 생성 완료 → {output_csv_path}")
        return output_csv_path
    except Exception as e:
        logger.error(f"❌ CSV 리포트 생성 실패: {e}", exc_info=True)
        return None

