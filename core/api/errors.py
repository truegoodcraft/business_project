from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    error: str = Field(...)
    message: str | None = None
    fields: dict | list | None = None


def error_envelope(code: str, message: str | None = None, fields: dict | list | None = None) -> dict:
    return {"detail": ErrorBody(error=code, message=message, fields=fields).model_dump()}


def normalize_http_exc(detail) -> dict:
    if isinstance(detail, str):
        return {"detail": {"error": "bad_request", "message": detail}}
    if isinstance(detail, dict):
        merged = dict(detail)
        merged.setdefault("error", "bad_request")
        if "message" not in merged and "error" in merged:
            merged["message"] = None
        return {"detail": merged}
    return {"detail": {"error": "bad_request"}}


def normalize_validation_err(err) -> dict:
    field_map: dict[str, str] = {}
    for entry in err.errors():
        loc = ".".join(str(part) for part in entry.get("loc", []) if part != "body")
        field_map[loc] = entry.get("msg", "invalid")
    return error_envelope("validation_error", fields=field_map)
