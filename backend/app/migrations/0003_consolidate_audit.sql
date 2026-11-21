-- Legacy audit_log rows are superseded by the hash-chained audit_chain.
-- Pre-production: no production data exists in audit_log (nothing has been deployed).
DROP TABLE IF EXISTS audit_log;
