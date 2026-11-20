from collections.abc import Iterable


def missing_documents(
    required: Iterable[str], submitted: Iterable[str]
) -> list[str]:
    """Return the unique missing document types in alphabetical order."""
    return sorted(set(required).difference(submitted))
