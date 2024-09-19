from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class LibraryException(Exception):
    """Base exception for library-related errors."""

    pass


class BookNotFoundError(LibraryException):
    def __init__(self, book_id: int):
        self.book_id = book_id
        super().__init__(f"Book with ID {book_id} not found")


class UserNotFoundError(LibraryException):
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")


class InvalidBookDataError(LibraryException):
    def __init__(self, message: str):
        super().__init__(f"Invalid book data: {message}")


class DatabaseError(LibraryException):
    def __init__(self, operation: str, details: str):
        super().__init__(f"Database error during {operation}: {details}")


class BookNotAvailableError(LibraryException):
    def __init__(self, book_id: int):
        self.book_id = book_id
        super().__init__(f"Book with ID {book_id} is not available for borrowing")


# Exception handlers
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


async def library_exception_handler(request: Request, exc: LibraryException):
    logger.error(f"Library error: {str(exc)}")
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)},
    )


def add_exception_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(
        ResponseValidationError, response_validation_exception_handler
    )
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(LibraryException, library_exception_handler)
