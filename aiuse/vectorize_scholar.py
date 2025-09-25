import os
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import psycopg2
import numpy as np
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


@dataclass
class DbConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = "2012"
    schema: str = "scholar"


def connect_db(cfg: DbConfig):
    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.dbname,
        user=cfg.user,
        password=cfg.password,
    )


def list_tables(conn, schema: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
              FROM information_schema.tables
             WHERE table_schema = %s AND table_type = 'BASE TABLE'
             ORDER BY table_name
            """,
            (schema,),
        )
        return [r[0] for r in cur.fetchall()]


def list_columns(conn, schema: str, table: str) -> List[Tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
             ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


def get_primary_key(conn, schema: str, table: str) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT kcu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.table_schema = kcu.table_schema
             WHERE tc.constraint_type = 'PRIMARY KEY'
               AND tc.table_schema = %s
               AND tc.table_name = %s
             ORDER BY kcu.ordinal_position
            """,
            (schema, table),
        )
        row = cur.fetchone()
        return row[0] if row else None


def fetch_samples(conn, schema: str, table: str, limit: int = 5) -> List[Dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {schema}.\"{table}\" LIMIT %s", (limit,))
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]


def get_text_columns(cols: List[Tuple[str, str]]) -> List[str]:
    text_types = {"text", "character varying", "character", "citext"}
    return [name for name, dtype in cols if dtype in text_types]


def build_text(row: Dict[str, object], text_cols: List[str]) -> str:
    parts: List[str] = []
    for c in text_cols:
        v = row.get(c)
        if v is None:
            continue
        parts.append(str(v))
    return "\n".join(parts)


def vectorize_rows(rows: List[Dict[str, object]], text_cols: List[str], n_components: int = 128) -> Tuple[np.ndarray, List[str]]:
    documents = [build_text(r, text_cols) for r in rows]
    # 빈 문서 제거 방지: 최소 공백 넣기
    documents = [d if d.strip() else "_" for d in documents]
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(documents)
    if X.shape[1] < n_components:
        n_components = max(2, X.shape[1])
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    dense = svd.fit_transform(X)
    return dense.astype(np.float32), documents


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_jsonl(path: str, records: List[Dict[str, object]]):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def inspect_and_vectorize(cfg: DbConfig, sample_limit: int = 5) -> None:
    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    ensure_dir(out_dir)

    with connect_db(cfg) as conn:
        tables = list_tables(conn, cfg.schema)
        print(f"[INFO] schema={cfg.schema} tables={len(tables)}: {tables}")

        summary: List[Dict[str, object]] = []
        for table in tables:
            cols = list_columns(conn, cfg.schema, table)
            text_cols = get_text_columns(cols)
            pk = get_primary_key(conn, cfg.schema, table)
            samples = fetch_samples(conn, cfg.schema, table, sample_limit)

            print(f"\n[INSPECT] {cfg.schema}.{table}")
            print(f"  columns: {cols}")
            print(f"  text_columns: {text_cols}")
            print(f"  primary_key: {pk}")
            print(f"  sample_rows: {len(samples)}")

            summary.append({
                "table": table,
                "columns": cols,
                "text_columns": text_cols,
                "primary_key": pk,
                "sample_count": len(samples),
            })

            if not text_cols or not samples:
                continue

            vectors, docs = vectorize_rows(samples, text_cols, n_components=128)
            recs: List[Dict[str, object]] = []
            for i, row in enumerate(samples):
                pk_val = row.get(pk) if pk else i
                recs.append({
                    "schema": cfg.schema,
                    "table": table,
                    "pk": pk_val,
                    "text": docs[i],
                    "vector": vectors[i].tolist(),
                })

            file_path = os.path.join(out_dir, f"{table}_vectors.jsonl")
            save_jsonl(file_path, recs)
            print(f"  -> saved vectors: {file_path} ({len(recs)} rows)")

        save_jsonl(os.path.join(out_dir, "_summary.jsonl"), summary)
        print(f"\n[DONE] Wrote summary and vectors to: {out_dir}")


def parse_args(argv: List[str]) -> DbConfig:
    # 간단 파서 (기본값은 문제에서 주신 값)
    cfg = DbConfig()
    for i, a in enumerate(argv):
        if a == "--host":
            cfg.host = argv[i + 1]
        elif a == "--port":
            cfg.port = int(argv[i + 1])
        elif a == "--db":
            cfg.dbname = argv[i + 1]
        elif a == "--user":
            cfg.user = argv[i + 1]
        elif a == "--password":
            cfg.password = argv[i + 1]
        elif a == "--schema":
            cfg.schema = argv[i + 1]
    return cfg


if __name__ == "__main__":
    cfg = parse_args(sys.argv[1:])
    inspect_and_vectorize(cfg, sample_limit=5)



