# RESEARCHER

[![CI](https://github.com/CherryCocacola/researcher/actions/workflows/ci.yml/badge.svg)](https://github.com/CherryCocacola/researcher/actions/workflows/ci.yml)

## 개요
RESEARCHER는 `scholar` PostgreSQL 스키마를 기반으로 연구자·논문·특허 데이터를 분석하고, 강화된 RAG + 벡터 검색으로 최적의 연구자를 추천합니다. 모든 응답은 Markdown 형식으로 반환되어 UI에서 읽기 쉽도록 렌더링됩니다.

## 주요 변경 사항 (2025-09)
- **스키마 전환**: 기존 `researcher` 전용 테이블 → `scholar.tb_*` 구조로 완전 이관
- **임베딩 파이프라인**: `intfloat/multilingual-e5-large` SentenceTransformer와 pgvector를 활용해 모든 테이블에 `embedding` 컬럼을 생성·적재 (`aiuse/embed_all_tables.py`)
- **추천 로직**: 임팩트 팩터 가중치, 논문/특허 키워드 중복 제거 및 한글 우선 정렬, 키워드 매칭 보너스를 적용
- **RAG & 프롬프트**: 추천 사유를 Markdown bullet 형식으로 생성하고, 상위 논문·저널 정보를 함께 제시
- **UI 개선**: 프런트엔드에서 Markdown을 렌더링하며 총점/보너스 내역을 시각화

## 실행법
### 1. 환경 변수 (.env)
```env
OPENAI_API_KEY=sk-...
DB_HOST=localhost
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=2012
DB_SCHEMA=scholar
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIM=1024
SIMILARITY_THRESHOLD=0.75
JOURNAL_IMPACT_WEIGHT=0.2
KEYWORD_WEIGHT=0.3
KEYWORD_LANGUAGE_PRIORITY=ko,en
```

### 2. 의존성
```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt  # (없다면 직접 psycopg2-binary, pgvector, sentence-transformers 등 설치)
```

### 3. 임베딩 생성
```bash
.venv\Scripts\python aiuse\embed_all_tables.py --schema scholar --dim 1024
```
- 이미 실행한 경우 스킵 가능
- `tb_semantic_node`의 기존 1024차원을 자동 감지하여 패딩/자르기 처리

### 4. 서버 실행
```bash
.venv\Scripts\python app.py
```
- 기본 포트: `http://localhost:5001`

## 구조
- `app.py`: Flask 엔드포인트 (`/recommend`, `/assist`, `/upload`)
- `core/config.py`: 환경 변수/하이퍼파라미터 관리
- `core/db.py`: `search_path` 기반 PostgreSQL 연결
- `core/vector_utils.py`: scholar 스키마 임베딩 로딩 및 FAISS 인덱스 구축
- `core/recommendation.py`: 벡터 검색 + 임팩트/키워드 가산점 + GPT Markdown 요약
- `templates/index.html`: Markdown 렌더링 및 Chart.js 기반 시각화
- `aiuse/embed_all_tables.py`: scholar 전체 테이블에 `embedding` 컬럼 생성/업데이트

## API 요약
| Endpoint | Method | 설명 |
| --- | --- | --- |
| `/recommend` | POST | `{"query": "..."}` 입력 → 추천 결과 리스트 (Markdown 사유 포함) |
| `/assist` | POST | 텍스트 → GPT 기반 분석 |
| `/upload` | POST | 이미지 업로드 → 분석 후 설명 |

## 테스트 체크리스트
1. `.venv` 활성화 후 `aiuse/embed_all_tables.py` 실행
2. `app.py` 실행 → `/recommend`에 `"AI 기반 화장품 연구"` 등 질의를 전송
3. 브라우저 UI에서 Markdown 사유/총점/차트 확인
4. Notion/CI/Notion sync 워크플로 상태 확인 (필요 시 GitHub Secrets 설정)

## 📊 WBS (Work Breakdown Structure) 프로젝트 관리

### Notion 연동 시스템
GitHub 이슈를 Notion WBS 보드로 자동 동기화하여 프로젝트 진행상황을 시각화합니다.

#### 설정 방법
1. **Notion 데이터베이스 생성** (다음 속성 포함):
   - `Name` (Title): 작업명
   - `Issue` (Number): GitHub 이슈 번호
   - `Status` (Select): 대기열, 계획중, 진행중, 검토중, 대기중, 완료
   - `Category` (Select): 백엔드, 프론트엔드, 데이터베이스, AI/ML, DevOps, 테스팅, 문서화, 보안, 성능, UI/UX, 기타
   - `Priority` (Select): P0, P1, P2, P3
   - `WBS Level` (Rich Text): 1.0, 1.1, 1.1.1 등
   - `Progress` (Number): 진행률 0-100%
   - `ETA` (Date): 예상 완료일
   - `Milestone` (Rich Text): 마일스톤
   - `Assignees` (Multi-select): 담당자
   - `URL` (URL): GitHub 이슈 링크

2. **GitHub Secrets 설정**:
   - `NOTION_TOKEN`: Notion 내부 통합 토큰
   - `NOTION_DATABASE_ID`: 위에서 만든 데이터베이스 ID

#### 이슈 라벨 규칙
GitHub 이슈에 다음 라벨을 추가하여 WBS 상태를 관리하세요:

**상태 라벨:**
- `in-progress` → 진행중
- `review`, `testing` → 검토중
- `blocked`, `waiting` → 대기중
- `planning`, `design` → 계획중

**카테고리 라벨:**
- `backend`, `frontend`, `database`, `ai`, `devops`, `testing`, `documentation`, `security`, `performance`, `ui/ux`

**우선순위 라벨:**
- `P0`, `P1`, `P2`, `P3` 또는 `priority:P0`, `priority:P1` 등

**기타 라벨:**
- `wbs:1.0`, `wbs:1.1` → WBS 레벨
- `eta:2025-01-15` → 예상 완료일
- `progress:75` → 진행률 75%
- `effort:5` → 작업량 5 Story Points

#### 자동 동기화
- **트리거**: 이슈 생성/수정/라벨 변경 시 자동 실행
- **스케줄**: 6시간마다 전체 동기화
- **수동 실행**: GitHub Actions에서 "WBS Notion Sync" 워크플로 실행

#### 사용 예시
```bash
# 이슈 생성 시 라벨 추가
gh issue create --title "API 성능 최적화" --label "backend,P1,in-progress,progress:25,eta:2025-01-20"

# 진행률 업데이트
gh issue edit 123 --add-label "progress:75"

# WBS 레벨 지정
gh issue edit 123 --add-label "wbs:2.1.3"
```

## 추가 작업 제안
- SentenceTransformer 캐싱 및 배치 인퍼런스 최적화
- pgvector 기반 서버 측 Top-k 검색 API 추가
- 추천 결과를 GitHub Pages 대시보드와 연동해 공유
