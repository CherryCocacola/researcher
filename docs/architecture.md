# Architecture Overview

## 현재 구성 요약
- Flask 기반 웹 애플리케이션 (`app.py`)
- 백엔드 모듈
  - `core/config.py`: 환경 변수와 모델/DB 설정 관리
  - `core/db.py`: PostgreSQL 연결 (`search_path` 기반 스키마 선택)
  - `core/vector_utils.py`: 연구자 임베딩 로딩 및 FAISS 인덱스 구성
  - `core/recommendation.py`: 연구자 추천 (임베딩 검색 + GPT 근거 생성)
  - `core/api.py`: 논문/연구자 검색 API
  - `core/analyzer.py`: 이미지/텍스트 분석
- 데이터 파이프라인 및 유틸리티
  - `aiuse/vectorize_scholar.py`: 스키마 탐색 + TF-IDF 임베딩 추출(JSONL)
  - `aiuse/embed_all_tables.py`: scholar.* 테이블에 `embedding` 컬럼 생성/적재
  - `migrations/001_init.sql`: 과거 researcher.* 스키마 정의

## 목표 전환 (researcher → scholar)
1. **스키마 지정**
   - `AppConfig`에 `db_schema` 기본값을 `scholar`로 지정하고 `search_path` 적용
   - 모든 SQL에서 하드코딩된 `researcher.` 접두사를 제거하고 `cfg.db_schema` 사용
2. **데이터 소스 매핑**
   - 기존 researcher.* 테이블 → scholar.* 테이블 매핑
   - 예시: `researcher.researcher_profile_vector` → `scholar.tb_researcher` + `tb_thesis`/`tb_patent` 조인으로 대체
   - 임베딩은 `aiuse/embed_all_tables.py`로 채운 `embedding` 컬럼 사용
3. **추천 로직 강화**
   - 고성능 SentenceTransformer(e.g. multilingual-e5-large)로 교체, DB vector 컬럼 차원 정리
   - 논문 임팩트, 키워드 중복 제거, 한글 우선 정렬, 특허 키워드 활용
   - 추천 점수 = 임베딩 유사도 + 임팩트/키워드 보너스
4. **RAG & 프롬프트 업그레이드**
   - pgvector 기반 검색 + 논문/특허 요약 결합
   - Structured prompt (system/context/user) 및 Markdown 출력 포맷 정립
5. **UI/응답 개선**
   - `/recommend` 응답을 Markdown 구조로 반환
   - 프런트에서 markdown 렌더링 적용(예: marked.js or showdown.js)

## 주요 테이블 매핑
- `tb_researcher`: 연구자 기본정보(이름/부서/이메일 등)
- `tb_thesis`: 논문 메타 + `impact_factor`, `grade`
- `tb_thesis_author`: 논문-연구자 매핑
- `tb_thesis_keyword`: 논문 키워드
- `tb_patent`, `tb_patent_keyword`, `tb_patent_holder`: 특허 및 키워드/소유자
- `tb_jounal`: 저널 정보(ISSN, Impact 확인용)
- `tb_semantic_node`: 기존 RAG 자료(embedding vector(1024) 유지)

## 향후 작업 순서
1. `config.py`, `db.py`, `vector_utils.py`, `api.py` 등에서 스키마/쿼리 수정
2. scholar 기반 데이터 로딩/임베딩/FAISS 재구성
3. 추천 점수 및 키워드 처리 로직 개선
4. RAG 파이프라인 및 프롬프트/응답 구조 리팩터링
5. 프런트엔드의 Markdown 렌더링 적용
6. README와 테스트 시나리오 업데이트



