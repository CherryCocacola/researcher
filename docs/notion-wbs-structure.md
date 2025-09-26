# Notion WBS 데이터베이스 구조 (간단 버전)

## 데이터베이스 이름: "Researcher WBS"

### 필수 필드 구성 (5개)

| 필드명 | 타입 | 설명 | 설정 |
|--------|------|------|------|
| **Title** | Title | 작업 이름/커밋 메시지 | 필수 |
| **Tags** | Multi-select | 상태, 담당자, 분류, 우선순위 | 아래 옵션들 |
| **Files** | Files & media | 관련 파일, 스크린샷 등 | 선택사항 |
| **plandate** | Date | 계획 예정일 | 사용자가 수동 입력 |
| **ExcuteDate** | Date | 실행 완료일 | 코드에서 자동 입력 |

### 태그 옵션 설정

**상태 태그:**
- `계획중` 🔵
- `진행중` 🟡
- `완료` 🟢
- `보류` 🟠

**담당자 태그:**
- `AI-Agent` 🤖
- `본인` 👤

**작업 분류 태그:**
- `개발` 💻
- `버그수정` 🐛
- `문서화` 📝
- `테스트` 🧪
- `배포` 🚀

**우선순위 태그:**
- `P0-긴급` 🔴
- `P1-높음` 🟠
- `P2-보통` 🟡
- `P3-낮음` 🟢

## 자동 동기화 작동 방식

1. **커밋 시 자동 생성**: Claude가 파일을 수정하고 커밋할 때마다 Notion에 작업 항목이 생성됩니다.

2. **태그 자동 분류**:
   - 커밋 메시지에 따라 자동으로 적절한 태그들이 추가됩니다
   - AI 작업은 `AI-Agent` 태그, 사용자 작업은 `본인` 태그

3. **예시 작업들**:
```
✅ AI 수정: app.py - 검색 기능 개선
   태그: 완료, AI-Agent, 개발, P2-보통

✅ 문서 업데이트: README.md 수정
   태그: 완료, 본인, 문서화, P2-보통

✅ 버그 수정: 데이터베이스 연결 오류 해결
   태그: 완료, AI-Agent, 버그수정, P2-보통
```

## 설정 가이드

1. **Notion에서 데이터베이스 생성**
   - 이름: "Researcher WBS"
   - 속성: 이름(Title), 태그(Multi-select), 파일(Files)

2. **환경변수 설정**
   ```env
   NOTION_TOKEN=your_notion_integration_token
   NOTION_WBS_DATABASE_ID=your_database_id
   ```

3. **GitHub Secrets 설정**
   - Repository → Settings → Secrets → Actions
   - 위 환경변수들을 Secrets로 등록