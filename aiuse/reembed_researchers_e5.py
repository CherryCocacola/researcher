import os
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2012")
DB_SCHEMA = os.getenv("DB_SCHEMA", "scholar")

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        options=f"-c search_path={DB_SCHEMA},public"
    )


def to_vec_literal(vec):
    arr = np.asarray(vec, dtype="float32").reshape(-1)
    if arr.shape[0] > DIM:
        arr = arr[:DIM]
    if arr.shape[0] < DIM:
        arr = np.pad(arr, (0, DIM - arr.shape[0]))
    return "[" + ",".join(f"{float(x):.6f}" for x in arr.tolist()) + "]"


def main():
    model = SentenceTransformer(MODEL_NAME)
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Ensure column vector(1024)
            cur.execute(
                """
                DO $$
                DECLARE fmt text;
                BEGIN
                  SELECT format_type(a.atttypid, a.atttypmod) INTO fmt
                    FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid=c.oid
                    JOIN pg_namespace n ON c.relnamespace=n.oid
                   WHERE n.nspname = current_schema()
                     AND c.relname = 'tb_researcher'
                     AND a.attname = 'embedding'
                     AND a.attnum > 0 AND NOT a.attisdropped;
                  IF fmt IS DISTINCT FROM 'vector(1024)' THEN
                    BEGIN
                      ALTER TABLE tb_researcher RENAME COLUMN "embedding" TO "embedding_old";
                    EXCEPTION WHEN undefined_column THEN
                    END;
                    ALTER TABLE tb_researcher ADD COLUMN IF NOT EXISTS "embedding" public.vector(1024);
                  END IF;
                END $$;
                """
            )
            conn.commit()

            # Load researcher name + keywords
            cur.execute(
                """
                SELECT r.researcher_id,
                       r.name,
                       COALESCE(array_agg(DISTINCT tk.term) FILTER (WHERE tk.term IS NOT NULL), '{}') AS thesis_keywords,
                       COALESCE(array_agg(DISTINCT pk.term) FILTER (WHERE pk.term IS NOT NULL), '{}') AS patent_keywords
                  FROM tb_researcher r
             LEFT JOIN tb_thesis_author ta ON ta.researcher_id = r.researcher_id
             LEFT JOIN tb_thesis_keyword tk ON tk.thesis_id = ta.thesis_id
             LEFT JOIN tb_patent_holder ph ON ph.researcher_id = r.researcher_id
             LEFT JOIN tb_patent_keyword pk ON pk.patent_id = ph.patent_id
              GROUP BY r.researcher_id, r.name
                """
            )
            rows = cur.fetchall()

            updated = 0
            for rid, name, rk, pk in rows:
                rk = rk or []
                pk = pk or []
                text = " ".join([str(name)] + [str(x) for x in rk] + [str(x) for x in pk])
                emb = model.encode(text)
                vec = to_vec_literal(emb)
                cur.execute(
                    'UPDATE tb_researcher SET "embedding" = (%s)::public.vector WHERE researcher_id = %s',
                    (vec, rid)
                )
                updated += 1

            conn.commit()
            print(f"[OK] updated {updated} researchers to vector(1024) using {MODEL_NAME}")


if __name__ == "__main__":
    main()


