# ASR 서버 테스트

## 실행 방법

### 전체 테스트 실행
```bash
cd backend/rk3588asr
pytest tests/ -v
```

### 특정 테스트 파일 실행
```bash
pytest tests/test_matcher.py -v
pytest tests/test_result_transmitter.py -v
pytest tests/test_config.py -v
```

### 커버리지 포함 실행
```bash
pytest tests/ --cov=rk3588asr --cov-report=html
```

## 테스트 구조

- `test_matcher.py`: 매칭 시스템 테스트
- `test_result_transmitter.py`: 결과 전송 모듈 테스트
- `test_config.py`: 설정 모듈 테스트

## 참고

- 테스트는 실제 모델 파일이 없어도 실행 가능하도록 작성됨
- 일부 테스트는 모의 객체(mock)를 사용하여 외부 의존성 제거

