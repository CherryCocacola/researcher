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

## 추가 작업 제안
- SentenceTransformer 캐싱 및 배치 인퍼런스 최적화
- pgvector 기반 서버 측 Top-k 검색 API 추가
- 추천 결과를 GitHub Pages 대시보드와 연동해 공유
