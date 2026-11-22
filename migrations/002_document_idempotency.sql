ALTER TABLE supplier_documents
    ADD COLUMN idempotency_key uuid,
    ADD CONSTRAINT supplier_document_request_key UNIQUE (supplier_id, idempotency_key);
