from typing import List
from psycopg2.extras import RealDictCursor
from core.db import get_connection

# 논문 키워드 기반 검색
def search_papers_by_keyword(keyword: str, limit: int = 20) -> List[dict]:
    """키워드를 포함하는 논문을 검색하여 기본 메타 및 키워드를 반환합니다."""
    sql = """
    SELECT t.thesis_id,
           t.title,
           j.name AS journal_name,
           t.grade,
           t.jcr,
           t.impact_factor,
           array_agg(DISTINCT tk.term) AS keywords,
           array_agg(DISTINCT ta.researcher_id) AS author_ids
      FROM tb_thesis t
 LEFT JOIN tb_thesis_keyword tk ON tk.thesis_id = t.thesis_id
 LEFT JOIN tb_thesis_author ta ON ta.thesis_id = t.thesis_id
 LEFT JOIN tb_jounal j ON j.journal_id = t.journal_id
     WHERE EXISTS (
           SELECT 1
             FROM tb_thesis_keyword tk2
            WHERE tk2.thesis_id = t.thesis_id
              AND tk2.term ILIKE %s
           )
  GROUP BY t.thesis_id, t.title, j.name, t.grade, t.jcr, t.impact_factor
  ORDER BY t.jcr DESC NULLS LAST, t.impact_factor DESC NULLS LAST
  LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (f"%{keyword}%", limit))
            return [dict(r) for r in cur.fetchall()]

# 연구자 이름 기반 검색
def search_researchers_by_name(name: str, limit: int = 20) -> List[dict]:
    """이름에 부분 일치하는 연구자를 검색하여 기초 통계를 반환합니다."""
    sql = """
    SELECT r.researcher_id,
           r.name,
           r.department,
           r.email,
           COUNT(DISTINCT ta.thesis_id) AS thesis_count,
           COUNT(DISTINCT ph.patent_id) AS patent_count
      FROM tb_researcher r
 LEFT JOIN tb_thesis_author ta ON ta.researcher_id = r.researcher_id
 LEFT JOIN tb_patent_holder ph ON ph.researcher_id = r.researcher_id
     WHERE r.name ILIKE %s
  GROUP BY r.researcher_id, r.name, r.department, r.email
  ORDER BY thesis_count DESC, patent_count DESC
  LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (f"%{name}%", limit))
            return [dict(r) for r in cur.fetchall()]
