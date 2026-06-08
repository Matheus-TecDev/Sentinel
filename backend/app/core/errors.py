from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Não foi possível concluir a solicitação"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": message,
                "details": exc.detail if not isinstance(exc.detail, str) else None,
            }
        },
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Dados inválidos",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )
