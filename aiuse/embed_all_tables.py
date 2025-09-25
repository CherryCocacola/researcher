import sys
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch
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
    dim: int = 128
    limit: Optional[int] = None


def connect_db(cfg: DbConfig):
    conn = psycopg2.connect(
        host=cfg.host, port=cfg.port, dbname=cfg.dbname,
        user=cfg.user, password=cfg.password
    )
    return conn


def ensure_extension(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()


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


def list_columns(conn, schema: str, table: str) -> List[Tuple[str, str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, udt_name
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
             ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [(r[0], r[1], r[2]) for r in cur.fetchall()]


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
               AND tc.table_schema = %s AND tc.table_name = %s
             ORDER BY kcu.ordinal_position
            """,
            (schema, table),
        )
        row = cur.fetchone()
        return row[0] if row else None


def text_columns(cols: List[Tuple[str, str, str]]) -> List[str]:
    text_types = {"text", "character varying", "character", "citext"}
    return [c for c, t, _ in cols if t in text_types]


def get_existing_embedding_dim(conn, schema: str, table: str) -> Optional[int]:
    with conn.cursor() as cur:
        # Check if 'embedding' column exists
        cur.execute(
            """
            SELECT a.atttypid, a.atttypmod,
                   format_type(a.atttypid, a.atttypmod) AS fmt,
                   t.typname
              FROM pg_attribute a
              JOIN pg_class c ON a.attrelid = c.oid
              JOIN pg_namespace n ON c.relnamespace = n.oid
              JOIN pg_type t ON a.atttypid = t.oid
             WHERE n.nspname = %s AND c.relname = %s AND a.attname = 'embedding' AND a.attnum > 0 AND NOT a.attisdropped
            """,
            (schema, table),
        )
        row = cur.fetchone()
        if not row:
            return None
        fmt = row[2]  # e.g., 'vector(1024)' or other
        typname = row[3]
        if typname != 'vector' and fmt != 'vector':
            return -1  # exists but not vector
        # Parse dimension from format_type
        if fmt.startswith('vector(') and fmt.endswith(')'):
            try:
                return int(fmt[len('vector('):-1])
            except Exception:
                return None
        return None


def ensure_embedding_column(conn, schema: str, table: str, desired_dim: int) -> int:
    """Ensure there is an 'embedding' vector(desired_dim) column; return effective dimension.
       Behaviors:
       - No column: add vector(desired_dim)
       - Exists but not vector: rename to embedding_old, add vector(desired_dim)
       - Exists as vector with different dim: rename to embedding_old, add vector(desired_dim)
       - Exists as vector with same dim: keep
    """
    dim = get_existing_embedding_dim(conn, schema, table)
    if dim is None:
        # no column -> create with desired_dim
        with conn.cursor() as cur:
            cur.execute(sql.SQL(
                'ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS "embedding" vector({})'
            ).format(sql.Identifier(schema), sql.Identifier(table), sql.Literal(desired_dim)))
        conn.commit()
        return desired_dim
    if dim == -1 or (dim and dim != desired_dim):
        # exists but not vector OR vector dim mismatch: rename and create
        with conn.cursor() as cur:
            # rename existing to embedding_old (avoid clobber)
            cur.execute(sql.SQL(
                'ALTER TABLE {}.{} RENAME COLUMN "embedding" TO "embedding_old"'
            ).format(sql.Identifier(schema), sql.Identifier(table)))
            # create fresh vector(desired_dim)
            cur.execute(sql.SQL(
                'ALTER TABLE {}.{} ADD COLUMN "embedding" vector({})'
            ).format(sql.Identifier(schema), sql.Identifier(table), sql.Literal(desired_dim)))
        conn.commit()
        return desired_dim
    # vector exists with same dimension
    return dim if dim else desired_dim


def fetch_rows(conn, schema: str, table: str, pk: Optional[str], text_cols: List[str], limit: Optional[int]):
    cols = ['ctid'] + ([pk] if pk else []) + text_cols
    q = sql.SQL("SELECT {} FROM {}.{}").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in cols),
        sql.Identifier(schema),
        sql.Identifier(table),
    )
    if limit:
        q = q + sql.SQL(" LIMIT {}").format(sql.Literal(limit))
    with conn.cursor() as cur:
        cur.execute(q)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]


def build_docs(rows, text_cols: List[str]) -> List[str]:
    docs = []
    for r in rows:
        parts = []
        for c in text_cols:
            v = r.get(c)
            if v is None:
                continue
            parts.append(str(v))
        docs.append("\n".join(parts) if parts else "_")
    return docs


def fit_embeddings(docs: List[str], dim: int) -> List[list]:
    vec = TfidfVectorizer(max_features=20000)
    X = vec.fit_transform(docs)
    dim_eff = min(dim, max(2, X.shape[1]))
    svd = TruncatedSVD(n_components=dim_eff, random_state=42)
    emb = svd.fit_transform(X)
    return emb.tolist()


def pad_or_truncate(embs: List[list], target_dim: int) -> List[list]:
    out: List[list] = []
    for e in embs:
        if len(e) == target_dim:
            out.append(e)
        elif len(e) < target_dim:
            out.append(e + [0.0] * (target_dim - len(e)))
        else:
            out.append(e[:target_dim])
    return out


def to_vec_literal(e: list) -> str:
    # pgvector는 '[x1, x2, ...]' 형식 문자열을 vector로 캐스팅 가능
    return '[' + ','.join(f"{float(x):.6f}" for x in e) + ']'


def update_embeddings(conn, schema: str, table: str, pk: Optional[str], rows, embs):
    with conn.cursor() as cur:
        if pk:
            data = [(to_vec_literal(embs[i]), rows[i][pk]) for i in range(len(rows))]
            execute_batch(cur, sql.SQL('UPDATE {}.{} SET "embedding" = (%s)::vector WHERE {} = %s').format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(pk)
            ).as_string(cur), data, page_size=500)
        else:
            data = [(to_vec_literal(embs[i]), rows[i]['ctid']) for i in range(len(rows))]
            execute_batch(cur, sql.SQL('UPDATE {}.{} SET "embedding" = (%s)::vector WHERE ctid = %s').format(
                sql.Identifier(schema), sql.Identifier(table)
            ).as_string(cur), data, page_size=500)
    conn.commit()


def parse_args(argv: List[str]) -> DbConfig:
    cfg = DbConfig()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--host": cfg.host = argv[i+1]; i += 2; continue
        if a == "--port": cfg.port = int(argv[i+1]); i += 2; continue
        if a == "--db": cfg.dbname = argv[i+1]; i += 2; continue
        if a == "--user": cfg.user = argv[i+1]; i += 2; continue
        if a == "--password": cfg.password = argv[i+1]; i += 2; continue
        if a == "--schema": cfg.schema = argv[i+1]; i += 2; continue
        if a == "--dim": cfg.dim = int(argv[i+1]); i += 2; continue
        if a == "--limit": cfg.limit = int(argv[i+1]); i += 2; continue
        i += 1
    return cfg


def main():
    cfg = parse_args(sys.argv[1:])
    conn = connect_db(cfg)
    try:
        ensure_extension(conn)
        tables = list_tables(conn, cfg.schema)
        print(f"[INFO] schema={cfg.schema} tables={len(tables)}: {tables}")
        for t in tables:
            cols = list_columns(conn, cfg.schema, t)
            tcols = text_columns(cols)
            if not tcols:
                print(f"[SKIP] {t}: no text columns")
                continue
            pk = get_primary_key(conn, cfg.schema, t)
            eff_dim = ensure_embedding_column(conn, cfg.schema, t, cfg.dim)
            rows = fetch_rows(conn, cfg.schema, t, pk, tcols, cfg.limit)
            if not rows:
                print(f"[SKIP] {t}: no rows")
                continue
            docs = build_docs(rows, tcols)
            embs = fit_embeddings(docs, min(cfg.dim, eff_dim))
            embs = pad_or_truncate(embs, eff_dim)
            update_embeddings(conn, cfg.schema, t, pk, rows, embs)
            print(f"[OK] {t}: {len(rows)} rows -> embedding vector({eff_dim})")
    finally:
        conn.close()
    print("[DONE]")


if __name__ == "__main__":
    main()
