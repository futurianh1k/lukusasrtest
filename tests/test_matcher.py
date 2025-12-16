# -*- coding: utf-8 -*-
"""
매칭 시스템 테스트
"""

import pytest
from rk3588asr.matcher import SpeechRecognitionMatcher


@pytest.fixture
def matcher():
    """테스트용 matcher 인스턴스"""
    ground_truths = [
        "도와줘 사람이 쓰러졌어",
        "화재가 발생했어",
        "의료진을 불러줘",
    ]
    labels = ["emergency", "emergency", "emergency"]
    return SpeechRecognitionMatcher(ground_truths, labels)


def test_find_best_match_exact(matcher):
    """정확한 매칭 테스트"""
    result = matcher.find_best_match("도와줘 사람이 쓰러졌어")
    assert result["best_match"] == "도와줘 사람이 쓰러졌어"
    assert result["similarity"] == 1.0


def test_find_best_match_similar(matcher):
    """유사한 매칭 테스트"""
    result = matcher.find_best_match("도와줘 사람 쓰러졌어")
    assert result["best_match"] == "도와줘 사람이 쓰러졌어"
    assert result["similarity"] > 0.8


def test_emergency_detection(matcher):
    """응급 상황 감지 테스트"""
    result = matcher.find_best_match("도와줘 사람이 쓰러졌어")
    assert result["is_emergency"] is True
    assert len(result["emergency_keywords"]) > 0


def test_non_emergency(matcher):
    """비응급 상황 테스트"""
    result = matcher.find_best_match("안녕하세요")
    assert result["is_emergency"] is False


def test_cer_calculation(matcher):
    """CER 계산 테스트"""
    ground_truth = "도와줘 사람이 쓰러졌어"
    asr_result = "도와줘 사람 쓰러졌어"
    
    cer = matcher.cer_direct(ground_truth, asr_result)
    assert 0.0 <= cer <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

