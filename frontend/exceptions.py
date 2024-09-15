from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# Custom DB Exceptions
class BookNotFoundError(Exception):
    """Raised when a book is not found in the database."""

    def __init__(self, book_id: int):
        self.message = f"Book with id {book_id} not found"
        super().__init__(self.message)


class BookNotAvailableError(Exception):
    """Raised when a book is not available for borrowing."""

    def __init__(self, book_id: int):
        self.message = f"Book with id {book_id} is not available"
        super().__init__(self.message)


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""

    def __init__(self, user_id: int):
        self.message = f"User with id {user_id} not found"
        super().__init__(self.message)


# Cusstom API Exceptions

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request parameters. Please check your input."},
    )


async def response_validation_exception_handler(
    request: Request, exc: ResponseValidationError
):
    logger.error(f"Response validation error: {exc.errors()}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "The server encountered an unexpected error. Please contact support."
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please contact support."},
    )


async def book_not_found_exception_handler(request: Request, exc: BookNotFoundError):
    logger.error(f"Book not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


async def book_not_available_exception_handler(
    request: Request, exc: BookNotAvailableError
):
    logger.error(f"Book not available: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


async def user_not_found_exception_handler(request: Request, exc: UserNotFoundError):
    logger.error(f"User not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


def add_exception_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(
        ResponseValidationError, response_validation_exception_handler
    )
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(BookNotFoundError, book_not_found_exception_handler)
    app.add_exception_handler(
        BookNotAvailableError, book_not_available_exception_handler
    )
    app.add_exception_handler(UserNotFoundError, user_not_found_exception_handler)
