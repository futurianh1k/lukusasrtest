# -*- coding: utf-8 -*-
"""
설정 모듈 테스트
"""

import pytest
import os
from rk3588asr.config import (
    MODEL_DIR,
    MODEL_PATH,
    TOKENS_PATH,
    GROUND_TRUTHS,
    LABELS,
)


def test_model_paths():
    """모델 경로 설정 테스트"""
    assert MODEL_DIR is not None
    assert MODEL_PATH is not None
    assert TOKENS_PATH is not None


def test_ground_truths():
    """정답 데이터 테스트"""
    assert isinstance(GROUND_TRUTHS, list)
    assert len(GROUND_TRUTHS) > 0


def test_labels():
    """라벨 데이터 테스트"""
    assert isinstance(LABELS, list)
    assert len(LABELS) == len(GROUND_TRUTHS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

