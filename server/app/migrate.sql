CREATE TABLE IF NOT EXISTS applications (
  id              SERIAL PRIMARY KEY,
  loan_type       TEXT NOT NULL,
  amount          NUMERIC(14,2) NOT NULL,
  term_months     INTEGER NOT NULL,
  monthly_income  NUMERIC(14,2) NOT NULL,
  full_name       TEXT NOT NULL,
  monthly_payment NUMERIC(14,2) NOT NULL,
  total_repaid    NUMERIC(14,2) NOT NULL,
  total_interest  NUMERIC(14,2) NOT NULL,
  status          TEXT NOT NULL DEFAULT 'new',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS applications_status_idx ON applications (status);
CREATE INDEX IF NOT EXISTS applications_created_at_idx ON applications (created_at DESC);
