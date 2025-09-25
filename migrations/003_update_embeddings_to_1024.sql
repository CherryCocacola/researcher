-- Update all tables in schema 'scholar' that have an "embedding" column
-- to use pgvector type vector(1024). If an existing "embedding" is not
-- vector(1024), it is renamed to "embedding_old" and a fresh column is added.

DO $$
DECLARE
    r RECORD;
    fmt TEXT;
BEGIN
    FOR r IN (
        SELECT c.table_schema, c.table_name
          FROM information_schema.columns c
         WHERE c.table_schema = 'scholar'
           AND c.column_name = 'embedding'
    ) LOOP
        SELECT format_type(a.atttypid, a.atttypmod)
          INTO fmt
          FROM pg_attribute a
          JOIN pg_class cls ON a.attrelid = cls.oid
          JOIN pg_namespace n ON cls.relnamespace = n.oid
         WHERE n.nspname = r.table_schema
           AND cls.relname = r.table_name
           AND a.attname = 'embedding'
           AND a.attnum > 0
           AND NOT a.attisdropped;

        IF fmt IS DISTINCT FROM 'vector(1024)' THEN
            -- Keep backup of old values
            EXECUTE format('ALTER TABLE %I.%I RENAME COLUMN "embedding" TO "embedding_old"', r.table_schema, r.table_name);
            -- Create new vector(1024)
            EXECUTE format('ALTER TABLE %I.%I ADD COLUMN "embedding" vector(1024)', r.table_schema, r.table_name);
        END IF;
    END LOOP;
END $$;

-- Note: Values are intentionally left NULL. Recompute/populate with your
-- embedding job, e.g.:
--   python aiuse/embed_all_tables.py --schema scholar --dim 1024



