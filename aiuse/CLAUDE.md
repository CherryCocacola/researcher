# Claude Code 설정

## 자동 커밋/푸시 설정

### 실행 명령어
- **린트**: `python -m flake8 . --exclude=.venv,__pycache__`
- **타입체크**: `python -m mypy . --ignore-missing-imports`
- **테스트**: `python -m pytest tests/ -v` (tests 디렉토리가 있는 경우)

### 훅 설정
파일 수정 후 자동으로 Git 커밋 및 푸시가 실행됩니다.

#### 사용법
Claude가 파일을 수정할 때마다 다음이 자동 실행됩니다:
1. 변경된 파일을 git에 추가
2. 수정 내용을 설명하는 커밋 메시지와 함께 커밋
3. 원격 저장소로 푸시

#### 커밋 메시지 형식
```
AI 수정: [파일명] - [수정 내용 요약]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## 프로젝트 정보
- **저장소**: https://github.com/CherryCocacola/researcher.git
- **브랜치**: main
- **언어**: Python
- **프레임워크**: Flask, SQLAlchemy

## 개발 가이드라인
- PEP 8 코딩 스타일 준수
- 함수와 클래스에 docstring 작성
- 타입 힌트 사용 권장
- 보안에 민감한 정보는 .env 파일 사용