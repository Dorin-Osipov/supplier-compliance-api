import re
from datetime import date
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

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
