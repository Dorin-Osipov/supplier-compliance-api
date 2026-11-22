import re
from datetime import date
from typing import Annotated, Self
from uuid import UUID, uuid4

from fastapi import FastAPI
from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints, model_validator

import storage
from compliance import Document, assess_supplier


def require_calendar_date(value: object) -> object:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Use a calendar date in YYYY-MM-DD format")
    return value


CalendarDate = Annotated[date, BeforeValidator(require_calendar_date)]
Kind = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Kind
    expires_on: CalendarDate


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[Kind]
    documents: list[Evidence]
    as_of: CalendarDate


class AssessmentResponse(BaseModel):
    compliant: bool
    missing: tuple[str, ...]
    expired: tuple[str, ...]


app = FastAPI(title="Supplier Compliance API")


@app.post("/assessments")
def assess(request: AssessmentRequest) -> AssessmentResponse:
    """Assess evidence already available and in effect on the supplied date."""
    documents = (Document(item.kind, item.expires_on) for item in request.documents)
    result = assess_supplier(request.required, documents, request.as_of)
    return AssessmentResponse(
        compliant=result.compliant, missing=result.missing, expired=result.expired
    )


class Submission(Evidence):
    valid_from: CalendarDate

    @model_validator(mode="after")
    def check_validity_period(self) -> Self:
        if self.expires_on < self.valid_from:
            raise ValueError("expires_on must be on or after valid_from")
        return self


class SubmissionReceipt(BaseModel):
    id: UUID


class StoredAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[Kind]
    as_of: CalendarDate


@app.post("/suppliers/{supplier_id}/documents", status_code=201)
def submit_document(supplier_id: UUID, evidence: Submission) -> SubmissionReceipt:
    """Append one certificate to this supplier's history."""
    document_id = uuid4()
    with storage.connect() as conn:
        conn.execute(
            """INSERT INTO supplier_documents (id, supplier_id, kind, valid_from, expires_on)
               VALUES (%s, %s, %s, %s, %s)""",
            (document_id, supplier_id, evidence.kind, evidence.valid_from, evidence.expires_on),
        )
    return SubmissionReceipt(id=document_id)


@app.post("/suppliers/{supplier_id}/assessments")
def assess_stored(supplier_id: UUID, request: StoredAssessmentRequest) -> AssessmentResponse:
    """Evaluate the supplier's recorded evidence for the requested coverage date."""
    with storage.connect() as conn:
        rows = conn.execute(
            """SELECT kind, expires_on FROM supplier_documents
               WHERE supplier_id = %s AND valid_from <= %s""",
            (supplier_id, request.as_of),
        )
        result = assess_supplier(request.required, (Document(*row) for row in rows), request.as_of)
    return AssessmentResponse(compliant=result.compliant, missing=result.missing, expired=result.expired)
