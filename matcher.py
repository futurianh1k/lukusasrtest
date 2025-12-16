# -*- coding: utf-8 -*-
"""
음성인식 매칭 시스템 모듈

음성인식 결과와 정답 문장을 비교하고 CER(Character Error Rate)를 계산하는 기능
"""

import re
import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher

# jiwer는 선택적 의존성으로 처리
try:
    from jiwer import compute_measures
    JIWER_AVAILABLE = True
except ImportError:
    compute_measures = None
    JIWER_AVAILABLE = False

logger = logging.getLogger(__name__)


class SpeechRecognitionMatcher:
    """음성인식 결과와 정답 문장을 비교하는 클래스"""

    EMERGENCY_KEYWORDS = [
        "도와줘", "살려줘", "119", "응급", "불이야", "화재",
        "심장", "호흡", "출혈", "사고", "구급차", "응급실",
        "알러지", "구토", "의식", "가스",
    ]

    def __init__(self, ground_truths: List[str], labels: List[str] = None):
        self.ground_truths = ground_truths
        self.labels = labels if labels else ["일상"] * len(ground_truths)
        self.evaluation_results = []

    def preprocess(self, text: str) -> str:
        """텍스트 전처리"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """두 텍스트 간 유사도 계산"""
        return SequenceMatcher(None, text1, text2).ratio()

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Levenshtein 거리 계산"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def character_accuracy(self, recognized: str, ground_truth: str) -> float:
        """문자 정확도 계산"""
        recognized = self.preprocess(recognized)
        ground_truth = self.preprocess(ground_truth)
        lev_dist = self.levenshtein_distance(recognized, ground_truth)
        max_len = max(len(recognized), len(ground_truth))
        if max_len == 0:
            return 1.0
        accuracy = 1.0 - (lev_dist / max_len)
        return max(0.0, accuracy)

    def detect_emergency_keywords(self, text: str) -> List[str]:
        """응급 키워드 감지"""
        detected = []
        text = self.preprocess(text)
        for keyword in self.EMERGENCY_KEYWORDS:
            if keyword in text:
                detected.append(keyword)
        return detected

    def find_best_match(self, recognized_text: str) -> Dict:
        """인식 결과와 가장 유사한 정답 찾기"""
        recognized_text = self.preprocess(recognized_text)
        best_match = ""
        best_similarity = 0.0
        best_index = -1
        best_accuracy = 0.0

        for idx, ground_truth in enumerate(self.ground_truths):
            gt = self.preprocess(ground_truth)
            similarity = self.calculate_similarity(recognized_text, gt)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = ground_truth
                best_index = idx
                best_accuracy = self.character_accuracy(recognized_text, ground_truth)

        emergency_keywords = self.detect_emergency_keywords(recognized_text)
        is_emergency = len(emergency_keywords) > 0

        # best_match에 대해 CER 계산
        cer_direct = None
        cer_jiwer_result = None
        if best_match:
            cer_direct = self.cer_direct(recognized_text, best_match)
            cer_jiwer_result = self.cer_jiwer(recognized_text, best_match)

        result = {
            "recognized": recognized_text,
            "best_match": best_match,
            "similarity": best_similarity,
            "accuracy": best_accuracy,
            "index": best_index,
            "label": self.labels[best_index] if best_index >= 0 else "unknown",
            "emergency_keywords": emergency_keywords,
            "is_emergency": is_emergency,
            "cer": cer_direct["CER"] if cer_direct else None,
            "cer_direct": cer_direct,
            "cer_jiwer": cer_jiwer_result["CER"] if cer_jiwer_result else None,
            "cer_jiwer_full": cer_jiwer_result,
        }
        self.evaluation_results.append(result)
        return result

    def reset_evaluation(self):
        """평가 결과 초기화"""
        self.evaluation_results = []

    def cer_direct(
        self,
        recognized: str,
        ground_truth: str,
        ignore_spaces: bool = True,
    ) -> Dict[str, float]:
        """
        직접 구현한 Levenshtein DP + traceback으로 CER 계산
        CER = (S + D + I) / N
          - N: 정답(GT) 전체 음절 수
          - S: 치환(substitution) 개수
          - D: 삭제(deletion) 개수
          - I: 삽입(insertion) 개수
        """
        # 전처리
        rec = self.preprocess(recognized)
        gt = self.preprocess(ground_truth)

        if ignore_spaces:
            rec = rec.replace(" ", "")
            gt = gt.replace(" ", "")

        ref_chars = list(gt)   # 정답(GT)
        hyp_chars = list(rec)  # 인식 결과

        r = len(ref_chars)
        h = len(hyp_chars)

        # DP 테이블 생성
        dp = [[0] * (h + 1) for _ in range(r + 1)]
        for i in range(r + 1):
            dp[i][0] = i   # 삭제
        for j in range(h + 1):
            dp[0][j] = j   # 삽입

        # DP 채우기
        for i in range(1, r + 1):
            for j in range(1, h + 1):
                cost = 0 if ref_chars[i - 1] == hyp_chars[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # 삭제 D
                    dp[i][j - 1] + 1,      # 삽입 I
                    dp[i - 1][j - 1] + cost,  # 치환 S or 일치(hit)
                )

        # traceback 으로 S, D, I 계산
        i, j = r, h
        S = D = I = 0

        while i > 0 or j > 0:
            # 삭제
            if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                D += 1
                i -= 1
            # 삽입
            elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
                I += 1
                j -= 1
            else:
                # 대각선 이동: 치환 또는 일치
                if i > 0 and j > 0 and ref_chars[i - 1] != hyp_chars[j - 1]:
                    S += 1
                i -= 1
                j -= 1

        N = r  # 정답 길이
        cer = (S + D + I) / N if N > 0 else 0.0

        return {
            "CER": cer,
            "S": S,
            "D": D,
            "I": I,
            "N": N,
        }

    def cer_jiwer(
        self,
        recognized: str,
        ground_truth: str,
        ignore_spaces: bool = True,
    ) -> Optional[Dict[str, float]]:
        """
        jiwer 라이브러리를 이용한 CER 계산
        (jiwer가 설치되어 있지 않으면 None 반환)
        """
        if not JIWER_AVAILABLE:
            logger.warning(
                "jiwer 라이브러리가 설치되어 있지 않습니다. `pip install jiwer` 후 사용하세요."
            )
            return None

        def char_transform(s: str):
            s = self.preprocess(s)
            if ignore_spaces:
                s = s.replace(" ", "")
            return list(s)

        measures = compute_measures(
            truth=ground_truth,
            hypothesis=recognized,
            truth_transform=char_transform,
            hypothesis_transform=char_transform,
        )

        S = measures["substitutions"]
        D = measures["deletions"]
        I = measures["insertions"]
        N = measures["reference_length"]
        cer = (S + D + I) / N if N > 0 else 0.0

        return {
            "CER": cer,
            "S": S,
            "D": D,
            "I": I,
            "N": N,
            "raw_measures": measures,
        }

