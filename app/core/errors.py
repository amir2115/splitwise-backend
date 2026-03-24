from fastapi import HTTPException, status


class DomainError(HTTPException):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details=None,
    ) -> None:
        error = {
            "code": code,
            "message": message,
        }
        if details is not None:
            error["details"] = details
        super().__init__(status_code=status_code, detail={"error": error})


class NotFoundError(DomainError):
    def __init__(self, entity: str) -> None:
        super().__init__(code="not_found", message=f"{entity} not found", status_code=status.HTTP_404_NOT_FOUND)
