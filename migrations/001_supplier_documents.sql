CREATE TABLE supplier_documents (
    id uuid PRIMARY KEY,
    supplier_id uuid NOT NULL,
    kind text NOT NULL CHECK (btrim(kind) <> ''),
    valid_from date NOT NULL,
    expires_on date NOT NULL CHECK (expires_on >= valid_from)
);

CREATE INDEX supplier_documents_history
    ON supplier_documents (supplier_id, valid_from);
