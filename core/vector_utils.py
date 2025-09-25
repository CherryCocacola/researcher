from typing import List, Tuple, Optional
import json
import numpy as np
import torch

# Optional FAISS acceleration
try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore

# psycopg2와 커서는 필수
import psycopg2
from psycopg2.extras import RealDictCursor

# sentence_transformers는 선택적 의존성으로 처리
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

from core.db import get_connection


class VectorUtils:
    """임베딩 인코딩과 후보 검색(NumPy/FAISS)을 담당하는 유틸리티."""
    def __init__(self, config):
        """모델 및 임베딩 데이터를 초기화하고 검색 인덱스를 준비합니다."""
        self.config = config
        self.model = None
        if SentenceTransformer is not None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = SentenceTransformer(config.embedding_model_name, device=device)

        self.embedding_dim = config.embedding_dim
        self.researcher_ids: List[str] = []
        self.researcher_names: List[str] = []
        self.researcher_vectors: List[np.ndarray] = []
        self.researcher_rk: List[List[str]] = []
        self.researcher_pk: List[List[str]] = []
        self.rk_cnt: List[int] = []
        self.pk_cnt: List[int] = []
        self._mat_norm: Optional[np.ndarray] = None
        self._faiss_index = None

        self._load_vectors()

    def _load_vectors(self) -> None:
        """DB에서 연구자 임베딩 및 키워드를 읽어와 메모리에 적재하고, 검색 인덱스를 구성합니다."""
        # DB에서 연구자 임베딩과 키워드 정보를 로드
        with get_connection(self.config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT r.researcher_id,
                           r.name,
                           r.embedding,
                           COALESCE(array_agg(DISTINCT tk.term) FILTER (WHERE tk.term IS NOT NULL), '{}') AS thesis_keywords,
                           COALESCE(array_agg(DISTINCT pk.term) FILTER (WHERE pk.term IS NOT NULL), '{}') AS patent_keywords
                      FROM tb_researcher r
                 LEFT JOIN tb_thesis_author ta ON ta.researcher_id = r.researcher_id
                 LEFT JOIN tb_thesis_keyword tk ON tk.thesis_id = ta.thesis_id
                 LEFT JOIN tb_patent_holder ph ON ph.researcher_id = r.researcher_id
                 LEFT JOIN tb_patent_keyword pk ON pk.patent_id = ph.patent_id
                 GROUP BY r.researcher_id, r.name, r.embedding
                    """
                )
                rows = cur.fetchall()

        for row in rows:
            vec = row["embedding"]
            if isinstance(vec, str):
                # 문자열이면 JSON으로 파싱 (단일/이중따옴표 혼용까지 보정)
                try:
                    vec = json.loads(vec)
                except json.JSONDecodeError:
                    vec = json.loads(vec.replace("'", '"'))

            vector = np.array(vec, dtype="float32")
            self.researcher_ids.append(row["researcher_id"])  # type: ignore[index]
            self.researcher_names.append(row["name"])  # type: ignore[index]
            self.researcher_vectors.append(vector)

            thesis_keywords = [kw for kw in (row.get("thesis_keywords") or []) if kw]
            patent_keywords = [kw for kw in (row.get("patent_keywords") or []) if kw]
            self.researcher_rk.append(thesis_keywords)
            self.researcher_pk.append(patent_keywords)
            self.rk_cnt.append(len(thesis_keywords))
            self.pk_cnt.append(len(patent_keywords))

        if not self.researcher_vectors:
            raise ValueError(
                "No researcher embeddings found in scholar schema. Run aiuse/embed_all_tables.py first."
            )

        # DB 값 기준으로 차원 보정 + 정규화 행렬/FAISS 인덱스 준비
        self.embedding_dim = int(len(self.researcher_vectors[0]))
        mat = np.vstack(self.researcher_vectors).astype("float32")
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
        self._mat_norm = mat / norms
        if faiss is not None:
            try:
                index = faiss.IndexFlatIP(self.embedding_dim)
                if hasattr(faiss, "get_num_gpus") and faiss.get_num_gpus() > 0:
                    res = faiss.StandardGpuResources()
                    index = faiss.index_cpu_to_gpu(res, 0, index)
                index.add(self._mat_norm)
                self._faiss_index = index
            except Exception:
                self._faiss_index = None

    def encode(self, text: str) -> np.ndarray:
        """문장을 임베딩 벡터로 인코딩하고 DB 차원에 맞춰 정렬합니다."""
        if self.model is None:
            raise RuntimeError(
                "sentence-transformers가 설치되지 않았습니다. pip install sentence-transformers 로 설치하세요."
            )
        vec = self.model.encode(text)
        arr = np.array(vec, dtype="float32")
        # DB 임베딩 차원에 맞춰 정렬 (차원 불일치 방지)
        if arr.ndim > 1:
            arr = arr.flatten()
        if arr.shape[0] > self.embedding_dim:
            arr = arr[: self.embedding_dim]
        elif arr.shape[0] < self.embedding_dim:
            pad = np.zeros(self.embedding_dim - arr.shape[0], dtype="float32")
            arr = np.concatenate([arr, pad], axis=0)
        return arr

    def get_all_data(self) -> Tuple[
        List[str],
        List[str],
        List[np.ndarray],
        List[int],
        List[int],
        List[List[str]],
        List[List[str]],
    ]:
        """연구자 ID/이름/벡터/키워드 통계를 반환합니다."""
        return (
            self.researcher_ids,
            self.researcher_names,
            self.researcher_vectors,
            self.rk_cnt,
            self.pk_cnt,
            self.researcher_rk,
            self.researcher_pk,
        )

    def topk(self, q: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """정규화 코사인 유사도 기준 상위 k개의 인덱스와 유사도를 반환합니다."""
        if self._mat_norm is None:
            raise RuntimeError("vector matrix not initialized")
        q = q.astype("float32")
        q = q / (np.linalg.norm(q) + 1e-8)
        q = q.reshape(1, -1)
        if self._faiss_index is not None:
            sims, idx = self._faiss_index.search(q, k)  # type: ignore[attr-defined]
            return idx[0], sims[0]
        sims = (self._mat_norm @ q.T).ravel()
        if k >= sims.shape[0]:
            order = np.argsort(-sims)
        else:
            part = np.argpartition(-sims, k)[:k]
            order = part[np.argsort(-sims[part])]
        return order, sims[order]


