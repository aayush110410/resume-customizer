from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PARSE_STATUS = {
    "INVALID_FILE_TYPE": 415,
    "EMPTY_FILE": 400,
    "ENCRYPTED_PDF": 422,
    "SCANNED_PDF": 422,
    "TOO_MANY_PAGES": 422,
    "CORRUPT_FILE": 422,
}


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable

    def body(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse({"error": exc.body()}, status_code=exc.status)
