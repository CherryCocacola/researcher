# core/recommendation.py

import numpy as np
from typing import List, Dict
from openai import OpenAI
from core.db import get_connection
from core.config import AppConfig


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """두 벡터의 코사인 유사도를 계산합니다."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def dedupe_keywords(keywords: List[str], lang_order: List[str]) -> List[str]:
    """키워드 중복을 제거하고 언어 우선순위에 따라 정렬합니다."""
    seen = set()
    result = []
    for kw in keywords:
        normalized = kw.strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)
    # 한국어 우선 정렬
    def order_key(word: str):
        for idx, lang in enumerate(lang_order):
            if lang == "ko" and any("가" <= ch <= "힣" for ch in word):
                return idx
            if lang == "en" and word.isascii():
                return idx
        return len(lang_order)
    return sorted(result, key=order_key)


def fetch_researcher_context(researcher_id: str, limit: int = 5) -> Dict[str, List[str]]:
    """연구자의 대표 논문 정보를 조회합니다."""
    sql = """
    SELECT t.thesis_id,
           t.title,
           COALESCE(t.impact_factor, 0) AS impact_factor,
           array_agg(DISTINCT tk.term) AS keywords,
           j.name AS journal_name
      FROM tb_thesis t
 LEFT JOIN tb_thesis_author ta ON ta.thesis_id = t.thesis_id
 LEFT JOIN tb_thesis_keyword tk ON tk.thesis_id = t.thesis_id
 LEFT JOIN tb_jounal j ON j.journal_id = t.journal_id
     WHERE ta.researcher_id = %s
  GROUP BY t.thesis_id, t.title, t.impact_factor, j.name
  ORDER BY t.impact_factor DESC NULLS LAST
  LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (researcher_id, limit))
            rows = cur.fetchall()
    papers = []
    for thesis_id, title, impact, keywords, journal in rows:
        keywords = keywords or []
        papers.append({
            "thesis_id": thesis_id,
            "title": title,
            "impact": float(impact or 0),
            "keywords": keywords,
            "journal": journal,
        })
    return {"papers": papers}


def similarity_to_score(sim: float) -> float:
    """유사도를 0~100 점수로 변환합니다."""
    return round(max(sim, 0.0) * 100, 2)


class ResearcherRecommender:
    """연구자 추천(유사도 계산, 점수화, 요약 생성)을 담당합니다."""
    def __init__(self, vector_utils, config: AppConfig):
        """벡터 유틸과 설정을 받아 추천 준비를 수행합니다."""
        self.vector_utils = vector_utils
        self.cfg = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model_name = config.openai_text_model_name
        (
            self.ids,
            self.names,
            self.vectors,
            self.rk_cnt,
            self.pk_cnt,
            self.rk,
            self.pk,
        ) = self.vector_utils.get_all_data()
        order = []
        for lang in self.cfg.keyword_language_priority.split(','):
            order.append(lang.strip())
        self.keyword_lang_order = order or ["ko", "en"]

    def recommend(self, query: str, top_k: int = None):
        """질의를 받아 상위 연구자 추천 결과를 반환합니다."""
        top_k = top_k or self.cfg.top_k
        q_vec = self.vector_utils.encode(query)
        # 1단계: 빠른 벡터 검색으로 상위 후보 추출
        idxs, sims = self.vector_utils.topk(q_vec, max(top_k * 10, top_k))
        prelim = []
        for i, s in zip(idxs.tolist(), sims.tolist()):
            if s >= self.cfg.similarity_threshold:
                prelim.append((i, s))
        if not prelim:
            return []
        prelim = prelim[:top_k]

        # 2단계: 모든 후보에 컨텍스트/요약(OpenAI) 수행 (요청에 따라 5명 모두)
        llm_cap = top_k
        results = []
        # 토큰 전처리(폴백 요약에 활용)
        tokens = [t.strip().lower() for t in query.replace(',', ' ').split() if t.strip()]
        for rank, (i, sim) in enumerate(prelim):
            base_score = similarity_to_score(sim)
            rk = dedupe_keywords(self.rk[i], self.keyword_lang_order)
            pk = dedupe_keywords(self.pk[i], self.keyword_lang_order)
            impact_bonus = 0.0
            keyword_bonus = self._keyword_bonus(query, rk, pk)
            context = {}
            top_papers = []

            # 폴백 요약(점수 언급 제거, 입력-연구자 유사내용 설명)
            matched = [kw for kw in rk if kw and (kw.lower() in tokens or any(tok in kw.lower() for tok in tokens))]
            matched_str = ", ".join(matched[:5]) if matched else (", ".join(rk[:5]) if rk else "연관 키워드 없음")
            summary_md = (
                f"{self.names[i]} 연구자는 사용자 입력과 '{matched_str}' 등에서 주제가 맞물립니다. "
                f"관련 연구 키워드와 대표 성과를 바탕으로 추천합니다."
            )

            if rank < llm_cap:
                context = fetch_researcher_context(self.ids[i])
                impact_bonus = self._journal_bonus(context)
                top_papers = (context.get("papers", []) or [])[:3]
                llm_text = self._summarize(query, self.names[i], rk, pk, context, base_score, impact_bonus, keyword_bonus).strip()
                if llm_text:
                    summary_md = llm_text

            score = base_score + impact_bonus + keyword_bonus
            references = [p.get("thesis_id") for p in (context.get("papers", []) if context else [])]
            results.append({
                "researcher_id": self.ids[i],
                "name": self.names[i],
                "base_score": round(base_score, 2),
                "score": round(score, 2),
                "impact_bonus": round(impact_bonus, 2),
                "keyword_bonus": round(keyword_bonus, 2),
                "research_keywords": rk,
                "paper_keywords": pk,
                "reason_markdown": summary_md,
                "references": references,
                "top_papers": top_papers,
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _journal_bonus(self, context: Dict) -> float:
        """논문 임팩트 합에 비례한 가산점을 계산합니다."""
        impact_sum = sum(p.get("impact", 0) for p in context.get("papers", []))
        return impact_sum * self.cfg.journal_impact_weight

    def _keyword_bonus(self, query: str, rk: List[str], pk: List[str]) -> float:
        """질의 토큰과 연구자 키워드의 겹침에 따른 가산점을 계산합니다."""
        all_keywords = set([kw.lower() for kw in rk + pk])
        tokens = [tok.strip().lower() for tok in query.replace(',', ' ').split() if tok.strip()]
        overlaps = len([t for t in tokens if t in all_keywords])
        return overlaps * self.cfg.keyword_weight

    def _summarize(self, query: str, name: str, rk: List[str], pk: List[str], context: Dict, base_score: float, impact_bonus: float, keyword_bonus: float) -> str:
        """OpenAI 텍스트 모델을 사용해 자연어 500자 이내 추천 사유를 생성합니다."""
        # 대표 논문 요약 문자열 생성(최대 3편)
        paper_summaries: List[str] = []
        for paper in context.get("papers", [])[:3]:
            journal = paper.get("journal") or ""
            impact = float(paper.get("impact") or 0)
            paper_summaries.append(f"{paper['title']}({journal}, IF {impact:.2f})")
        papers_str = ", ".join(paper_summaries)

        # 자연어 단락 요약 생성(점수 언급 제거, 입력-연구자 유사내용 설명)
        prompt = (
            "당신은 연구자 추천 시스템입니다. 아래 정보를 바탕으로 한국어 자연문 단락으로 간결하게 요약하세요. "
            "반드시 500자 이내로 쓰고, 마크다운/목록/특수기호 없이 문장으로만 작성하십시오. 반말을 쓰지 말고 존중하는 어조로 작성하세요.\n\n"
            f"사용자 질의: {query}\n"
            f"연구자: {name}\n"
            f"연구 키워드: {', '.join(rk) if rk else '없음'}\n"
            f"논문 키워드: {', '.join(pk) if pk else '없음'}\n"
            f"대표 논문: {papers_str if papers_str else '없음'}\n\n"
            "요약 지침: 점수 언급은 하지 말고, 사용자 입력 내용과 연구자의 연구주제/키워드가 어떻게 겹치는지 구체적으로 설명하세요. "
            "대표 성과를 한두 개 덧붙이고, 불필요한 나열은 피하여 자연스러운 단락으로 작성하세요."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "당신은 전문 연구자 추천 시스템입니다. 한국어로 정중하고 간결한 문장 단락(500자 이내)만 작성하세요."},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=min(self.cfg.rag_max_tokens, 350),
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"- 사유 생성 실패: {e}"
