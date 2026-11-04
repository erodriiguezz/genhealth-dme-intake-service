"""initial schema

Revision ID: 0002
Revises: 0001

The DDL below is docs/architecture/schema.sql verbatim (minus BEGIN/COMMIT, which
Alembic's transaction provides). `make schema-diff` keeps the two in step.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA_SQL = r"""
CREATE EXTENSION IF NOT EXISTS citext;      -- case-insensitive email

-- -----------------------------------------------------------------------------
-- Types
-- -----------------------------------------------------------------------------

-- Derived by the API (app/validation/status.py). Never client-settable.
--   ready        = all 5 fields non-null AND no issue with severity 'error'
--   needs_review = anything else
-- Scaling path (not built): 'processing', 'failed' for async extraction (B2).
CREATE TYPE order_status AS ENUM ('needs_review', 'ready');

-- -----------------------------------------------------------------------------
-- updated_at trigger (shared)
-- -----------------------------------------------------------------------------

CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------

CREATE TABLE users (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email          citext      NOT NULL,
  password_hash  text        NOT NULL,          -- argon2id ($argon2id$v=19$...), never returned or logged
  created_at     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT users_email_key           UNIQUE (email),
  CONSTRAINT users_email_shape_chk     CHECK (email = btrim(email) AND length(email) BETWEEN 3 AND 254 AND position('@' in email) > 1),
  CONSTRAINT users_password_hash_chk   CHECK (password_hash LIKE '$argon2id$%')
);

COMMENT ON TABLE  users               IS 'Accounts. Reviewer accounts are seeded from SEED_USERS (app/seed.py).';
COMMENT ON COLUMN users.email         IS 'Login identifier, case-insensitive, trimmed.';
COMMENT ON COLUMN users.password_hash IS 'argon2id hash. Plaintext passwords are never stored.';

-- -----------------------------------------------------------------------------
-- documents: uploaded PDFs (decision D11/D15: stored for the review preview)
-- -----------------------------------------------------------------------------

CREATE TABLE documents (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id     uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  filename     text        NOT NULL,            -- sanitized client filename, display only
  sha256       char(64)    NOT NULL,            -- hex digest of content (dedupe hint, not unique)
  size_bytes   integer     NOT NULL,
  page_count   integer     NOT NULL,
  content      bytea       NOT NULL,            -- [PHI] the PDF; never selected in list queries
  created_at   timestamptz NOT NULL DEFAULT now(),

  -- Target of the composite FK from orders, so an order can only point at a
  -- document owned by the same user.
  CONSTRAINT documents_id_owner_key   UNIQUE (id, owner_id),
  CONSTRAINT documents_filename_chk   CHECK (length(filename) BETWEEN 1 AND 255 AND filename !~ '[/\\]'),
  CONSTRAINT documents_sha256_chk     CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  CONSTRAINT documents_size_chk       CHECK (size_bytes BETWEEN 1 AND 20971520),   -- 20 MB
  CONSTRAINT documents_pages_chk      CHECK (page_count BETWEEN 1 AND 100),
  CONSTRAINT documents_content_chk    CHECK (octet_length(content) = size_bytes)
);

CREATE INDEX documents_owner_idx ON documents (owner_id);

COMMENT ON TABLE  documents         IS 'Source PDFs, owner-scoped, served only via GET /orders/{id}/document. S3 is the scaling path (B3).';
COMMENT ON COLUMN documents.content IS '[PHI] Raw PDF bytes. Deferred-loaded by the ORM.';

-- -----------------------------------------------------------------------------
-- orders
-- -----------------------------------------------------------------------------

CREATE TABLE orders (
  id                  uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id            uuid         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  document_id         uuid,                                  -- null for manual orders
  status              order_status NOT NULL DEFAULT 'needs_review',

  -- The five extracted fields. All nullable: null means "not found / not
  -- provided", never "guessed". Values are kept as read (D16).
  patient_first_name  text,                                  -- [PHI]
  patient_last_name   text,                                  -- [PHI]
  patient_dob         date,                                  -- [PHI] null if missing OR unparseable (raw kept in extraction)
  provider_name       text,                                  -- as printed, credentials included
  provider_npi        varchar(20),                           -- separators stripped. May be invalid (flagged, not rejected)

  issues              jsonb        NOT NULL DEFAULT '[]'::jsonb,   -- current validation results
  extraction          jsonb,                                       -- provenance; null for manual orders; immutable

  created_at          timestamptz  NOT NULL DEFAULT now(),
  updated_at          timestamptz  NOT NULL DEFAULT now(),

  -- One order per document, and only a document owned by the same user.
  CONSTRAINT orders_document_key       UNIQUE (document_id),
  CONSTRAINT orders_document_owner_fk  FOREIGN KEY (document_id, owner_id)
                                       REFERENCES documents (id, owner_id) ON DELETE CASCADE,

  -- Shape and size only. Content validity is the validators' job.
  CONSTRAINT orders_first_name_len_chk CHECK (patient_first_name IS NULL OR length(patient_first_name) BETWEEN 1 AND 200),
  CONSTRAINT orders_last_name_len_chk  CHECK (patient_last_name  IS NULL OR length(patient_last_name)  BETWEEN 1 AND 200),
  CONSTRAINT orders_provider_len_chk   CHECK (provider_name      IS NULL OR length(provider_name)      BETWEEN 1 AND 300),
  CONSTRAINT orders_npi_len_chk        CHECK (provider_npi       IS NULL OR length(provider_npi)       BETWEEN 1 AND 20),
  CONSTRAINT orders_issues_array_chk   CHECK (jsonb_typeof(issues) = 'array'),
  CONSTRAINT orders_extraction_obj_chk CHECK (extraction IS NULL OR jsonb_typeof(extraction) = 'object'),
  CONSTRAINT orders_extraction_doc_chk CHECK (extraction IS NULL OR document_id IS NOT NULL),

  -- Defense in depth for the status rule: 'ready' requires all fields present
  -- and no error-severity issue. (The API derives status. This makes a
  -- bug there fail loudly instead of saving a wrong 'ready'.)
  CONSTRAINT orders_ready_complete_chk CHECK (
    status <> 'ready' OR (
          patient_first_name IS NOT NULL
      AND patient_last_name  IS NOT NULL
      AND patient_dob        IS NOT NULL
      AND provider_name      IS NOT NULL
      AND provider_npi       IS NOT NULL
      AND NOT jsonb_path_exists(issues, '$[*] ? (@.severity == "error")')
    )
  )
);

-- List endpoint: the caller's orders, newest first, optionally by status.
CREATE INDEX orders_owner_created_idx ON orders (owner_id, created_at DESC);
CREATE INDEX orders_owner_status_idx  ON orders (owner_id, status);

CREATE TRIGGER orders_set_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE  orders            IS 'DME orders. Owner-scoped. Status derived from issues.';
COMMENT ON COLUMN orders.status     IS 'Derived server-side. ready iff 5 fields non-null and no error issue.';
COMMENT ON COLUMN orders.issues     IS 'Array of {field, code, severity: error|warning, message, source: validation|extraction}. See schema.md.';
COMMENT ON COLUMN orders.extraction IS 'Extractor provenance: model, prompt_version, latency, tokens, per-field {raw, evidence, page, grounded}, provider_candidates.';
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SCHEMA_SQL.replace("%", "%%"))


def downgrade() -> None:
    op.execute("DROP TABLE orders, documents, users")
    op.execute("DROP FUNCTION set_updated_at()")
    op.execute("DROP TYPE order_status")
