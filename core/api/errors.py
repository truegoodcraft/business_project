from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    error: str = Field(...)
    message: str | None = None
    fields: dict | list | None = None


def error_envelope(code: str, message: str | None = None, fields: dict | list | None = None) -> dict:
    return {"detail": ErrorBody(error=code, message=message, fields=fields).model_dump()}


def normalize_http_exc(detail) -> dict:
    if isinstance(detail, str):
        return error_envelope("bad_request", detail)
    if isinstance(detail, dict) and "error" in detail:
        return error_envelope(detail["error"], detail.get("message"), detail.get("fields") or detail.get("errors"))
    return error_envelope("bad_request")


def normalize_validation_err(err) -> dict:
    field_map: dict[str, str] = {}
    for entry in err.errors():
        loc = ".".join(str(part) for part in entry.get("loc", []) if part != "body")
        field_map[loc] = entry.get("msg", "invalid")
    return error_envelope("validation_error", fields=field_map)
