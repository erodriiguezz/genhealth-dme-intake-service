-- =============================================================================
-- DME order-intake service: full database schema (PostgreSQL 16)
--
-- This is the reviewable source of truth for the data model. Alembic migration
-- 0002 (services/api/alembic/versions/0002_initial_schema.py) must produce exactly this
-- schema. CI-free check: `make schema-diff` dumps the migrated DB with
-- `pg_dump --schema-only` and diffs it against this file (added in M2).
--
-- Companion docs: schema.md (rationale, JSON shapes, issue codes),
-- api.md (how each column surfaces in the API).
--
-- Conventions
--   * UUID primary keys (gen_random_uuid, core since PG13): no enumerable ids.
--   * timestamptz everywhere, stored UTC.
--   * Ownership: every user-owned row carries owner_id. The API filters on it.
--     The DB enforces that an order and its document share one owner.
--   * PHI columns are marked [PHI]. No PHI goes in logs, indexes on PHI are
--     avoided, and nothing PHI-derived appears in constraint names or errors.
--   * PHI in errors: Postgres puts the whole failing row in constraint-violation
--     DETAIL ("Failing row contains (... Marie ...)"), seen while testing this file.
--     So (1) the API catches IntegrityError and logs only the constraint name,
--     never str(exc), and (2) the DB runs with log_error_verbosity = terse, set
--     at deploy, so the server log drops DETAIL.
--   * Values are stored AS READ from the document (decision D16). Constraints
--     limit shape and size, but never reject a value the validators would merely
--     flag. Validity lives in orders.issues, not in CHECKs.
-- =============================================================================

BEGIN;

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

COMMIT;

-- =============================================================================
-- Reference: JSONB shapes (enforced by Pydantic in app/schemas.py, not by PG)
-- =============================================================================
--
-- orders.issues  (JSON Schema draft 2020-12)
-- {
--   "type": "array",
--   "items": {
--     "type": "object",
--     "additionalProperties": false,
--     "required": ["field", "code", "severity", "message", "source"],
--     "properties": {
--       "field":    { "enum": ["patient_first_name","patient_last_name","patient_dob","provider_name","provider_npi"] },
--       "code":     { "type": "string", "pattern": "^[a-z_]+\\.[a-z_0-9]+$" },
--       "severity": { "enum": ["error","warning"] },
--       "message":  { "type": "string", "maxLength": 300 },
--       "source":   { "enum": ["validation","extraction"] }
--     }
--   }
-- }
--
-- orders.extraction
-- {
--   "type": "object",
--   "additionalProperties": false,
--   "required": ["provider","model","prompt_version","latency_ms","fields","provider_candidates"],
--   "properties": {
--     "provider":       { "enum": ["anthropic","bedrock","fake"] },
--     "model":          { "type": "string" },
--     "prompt_version": { "type": "string" },
--     "latency_ms":     { "type": "integer", "minimum": 0 },
--     "input_tokens":   { "type": ["integer","null"] },
--     "output_tokens":  { "type": ["integer","null"] },
--     "fields": {
--       "type": "object",
--       "additionalProperties": false,
--       "required": ["patient_first_name","patient_last_name","patient_dob","provider_name","provider_npi"],
--       "properties": {
--         "<each field>": {
--           "type": "object",
--           "required": ["raw","evidence","page","grounded"],
--           "properties": {
--             "raw":      { "type": ["string","null"] },
--             "evidence": { "type": ["string","null"], "maxLength": 500 },
--             "page":     { "type": ["integer","null"], "minimum": 1 },
--             "grounded": { "type": "boolean" }
--           }
--         }
--       }
--     },
--     "provider_candidates": {
--       "type": "array",
--       "items": {
--         "type": "object",
--         "required": ["name","role","npi","page"],
--         "properties": {
--           "name": { "type": "string" },
--           "role": { "type": "string" },
--           "npi":  { "type": ["string","null"] },
--           "page": { "type": ["integer","null"], "minimum": 1 }
--         }
--       }
--     },
--     "notes": { "type": ["string","null"] }
--   }
-- }
--
-- =============================================================================
-- Example rows (synthetic benchmark, after upload of the CPAP fax)
-- =============================================================================
--
-- orders:
--   status             = 'needs_review'
--   patient_first_name = 'Marie'        patient_last_name = 'Curie'
--   patient_dob        = '1900-12-05'   provider_name     = 'Arjun Raj D.P.M'
--   provider_npi       = '9182734556'   -- fails Luhn: kept as read, flagged
--   issues = [
--     {"field":"provider_npi","code":"npi.checksum_failed","severity":"error",  "message":"Fails the NPI checksum…","source":"validation"},
--     {"field":"patient_dob", "code":"dob.age_over_120",  "severity":"warning","message":"Patient would be 124…",  "source":"validation"},
--     {"field":"provider_name","code":"provider.multiple_candidates","severity":"warning","message":"Also on the document: Gregory House MD…","source":"extraction"}
--   ]
--
-- After PATCH provider_npi='1234567893': the issues drop the npi error, and
-- status becomes 'ready' (the warnings remain and don't block).
