from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date


def missing_documents(
    required: Iterable[str], submitted: Iterable[str]
) -> list[str]:
    """Return the unique missing document types in alphabetical order."""
    return sorted(set(required).difference(submitted))


@dataclass(frozen=True)
class Document:
    kind: str
    expires_on: date


@dataclass(frozen=True)
class Assessment:
    missing: tuple[str, ...]
    expired: tuple[str, ...]

    @property
    def compliant(self) -> bool:
        return not (self.missing or self.expired)


def assess_supplier(
    required: Iterable[str], documents: Iterable[Document], as_of: date
) -> Assessment:
    """Assess the supplied evidence, counting the expiry date as a valid day."""
    requirements = set(required)
    submitted = set()
    valid = set()
    for document in documents:
        if document.kind in requirements:
            submitted.add(document.kind)
            if document.expires_on >= as_of:
                valid.add(document.kind)

    return Assessment(
        missing=tuple(sorted(requirements - submitted)),
        expired=tuple(sorted(submitted - valid)),
    )
