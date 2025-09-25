from typing import Iterable, Optional
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from core.db import get_connection


def _bool_from_ox(value: object) -> bool:
    s = str(value).strip().upper()
    return s == 'O' or s == 'Y' or s == 'TRUE'


def _split_keywords(text: Optional[str]) -> Iterable[str]:
    if text is None:
        return []
    s = str(text)
    if not s:
        return []
    # split by common separators
    parts = []
    for sep in [';', ',', '\n', '\t', '·', '•']:
        if sep in s:
            s = s.replace(sep, ',')
    for token in s.split(','):
        token = token.strip()
        if token:
            parts.append(token)
    return parts


def ingest_excel_to_db(excel_path: Path):
    xls = pd.ExcelFile(excel_path, engine='openpyxl')
    sheets = {name: xls.parse(name) for name in xls.sheet_names}

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Researchers
                if '연구자' in sheets:
                    df = sheets['연구자']
                    rows = []
                    for _, r in df.iterrows():
                        rows.append((
                            int(r['사용자번호']),
                            str(r['연구자명']),
                            str(r.get('소속', '') or ''),
                            str(r.get('직급', '') or ''),
                            str(r.get('연락처', '') or ''),
                            str(r.get('이메일', '') or ''),
                            str(r.get('전공', '') or ''),
                            str(r.get('연구실 위치', '') or ''),
                            str(r.get('실험실', '') or ''),
                            str(r.get('웹사이트', '') or ''),
                            str(r.get('주요약력', '') or ''),
                            str(r.get('주요경력', '') or ''),
                            str(r.get('연구분야', '') or ''),
                        ))
                    execute_values(cur,
                        """
                        INSERT INTO researcher (
                            researcher_id, name, department, rank, phone, email, major,
                            office_location, lab_name, website, biography, career, research_area
                        ) VALUES %s
                        ON CONFLICT (researcher_id) DO UPDATE SET
                            name=EXCLUDED.name,
                            department=EXCLUDED.department,
                            rank=EXCLUDED.rank,
                            phone=EXCLUDED.phone,
                            email=EXCLUDED.email,
                            major=EXCLUDED.major,
                            office_location=EXCLUDED.office_location,
                            lab_name=EXCLUDED.lab_name,
                            website=EXCLUDED.website,
                            biography=EXCLUDED.biography,
                            career=EXCLUDED.career,
                            research_area=EXCLUDED.research_area
                        """,
                        rows
                    )

                # Papers and authors and keywords
                if '논문' in sheets:
                    df = sheets['논문']
                    paper_rows = []
                    author_rows = []
                    keyword_rows = []
                    for _, r in df.iterrows():
                        pid = int(r['순번'])
                        paper_rows.append((
                            pid,
                            str(r.get('제목', '') or ''),
                            str(r.get('논문등급', '') or ''),
                            str(r.get('발행기관', '') or ''),
                            str(r.get('ISBN', '') or ''),
                            str(r.get('발행국가', '') or ''),
                            float(r.get('JCR', 0) or 0),
                            float(r.get('IF', 0) or 0),
                            _bool_from_ox(r.get('노션여부', 'X')),
                            _bool_from_ox(r.get('ISBN온라인여부', 'X')),
                        ))

                        rid = int(r.get('사용자번호'))
                        is_corr = _bool_from_ox(r.get('교신저자여부', 'X'))
                        author_rows.append((pid, rid, is_corr))

                        for kw in _split_keywords(r.get('키워드')):
                            keyword_rows.append((pid, kw))

                    execute_values(cur,
                        """
                        INSERT INTO paper (
                            paper_id, title, grade, publisher, issn, country, jcr, impact_factor, notion_flag, online_issn_flag
                        ) VALUES %s
                        ON CONFLICT (paper_id) DO UPDATE SET
                            title=EXCLUDED.title,
                            grade=EXCLUDED.grade,
                            publisher=EXCLUDED.publisher,
                            issn=EXCLUDED.issn,
                            country=EXCLUDED.country,
                            jcr=EXCLUDED.jcr,
                            impact_factor=EXCLUDED.impact_factor,
                            notion_flag=EXCLUDED.notion_flag,
                            online_issn_flag=EXCLUDED.online_issn_flag
                        """,
                        paper_rows
                    )

                    execute_values(cur,
                        """
                        INSERT INTO paper_author (paper_id, researcher_id, is_corresponding)
                        VALUES %s
                        ON CONFLICT (paper_id, researcher_id) DO UPDATE SET
                            is_corresponding = EXCLUDED.is_corresponding
                        """,
                        author_rows
                    )

                    if keyword_rows:
                        execute_values(cur,
                            """
                            INSERT INTO paper_keyword (paper_id, keyword)
                            VALUES %s
                            ON CONFLICT (paper_id, keyword) DO NOTHING
                            """,
                            keyword_rows
                        )

                # Patents
                if '특허' in sheets:
                    df = sheets['특허']
                    rows = []
                    for _, r in df.iterrows():
                        rows.append((
                            int(r['순번']),
                            str(r.get('기술구분', '') or ''),
                            str(r.get('기술명', '') or ''),
                            str(r.get('기술분류', '') or ''),
                            str(r.get('대표 발명자', '') or ''),
                            int(r.get('대표 발명자 번호')) if pd.notna(r.get('대표 발명자 번호')) else None,
                            str(r.get('키워드', '') or ''),
                        ))
                    execute_values(cur,
                        """
                        INSERT INTO patent (
                            patent_id, tech_type, title, category, lead_inventor_name, lead_inventor_id, keywords
                        ) VALUES %s
                        ON CONFLICT (patent_id) DO UPDATE SET
                            tech_type=EXCLUDED.tech_type,
                            title=EXCLUDED.title,
                            category=EXCLUDED.category,
                            lead_inventor_name=EXCLUDED.lead_inventor_name,
                            lead_inventor_id=EXCLUDED.lead_inventor_id,
                            keywords=EXCLUDED.keywords
                        """,
                        rows
                    )

                # Pseudonym
                if '가명처리' in sheets:
                    df = sheets['가명처리']
                    if df.shape[1] >= 2:
                        id_col = df.columns[0]
                        name_col = df.columns[1]
                        rows = []
                        for _, r in df.iterrows():
                            rows.append((int(r[id_col]), str(r[name_col])))
                        execute_values(cur,
                            """
                            INSERT INTO pseudonym (researcher_id, pseudonym)
                            VALUES %s
                            ON CONFLICT (researcher_id) DO UPDATE SET
                                pseudonym=EXCLUDED.pseudonym
                            """,
                            rows
                        )
    finally:
        conn.close()


