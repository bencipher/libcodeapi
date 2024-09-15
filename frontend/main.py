from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from frontend.crud import (
    borrow_book,
    create_user_record,
    filter_books,
    get_book,
    get_books,
)
from frontend.exceptions import add_exception_handlers
from frontend.schemas import (
    BookFilterParams,
    BookSchema,
    BorrowSchema,
    UserCreate,
    UserSchema,
)
from frontend.storage import SessionLocal

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta


app = FastAPI()

add_exception_handlers(app)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Endpoints
@app.post("/users/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = create_user_record(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/books/", response_model=List[BookSchema], status_code=status.HTTP_200_OK)
def list_books(db: Session = Depends(get_db)):
    books = get_books(db)
    if books is None:
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching books"
        )
    if not books:
        raise HTTPException(status_code=404, detail="No books found")
    return books


@app.get("/books/filter", response_model=List[BookSchema])
def filter_book_records(
    params: BookFilterParams = Depends(),
    db: Session = Depends(get_db),
):
    books = filter_books(db, params.category, params.publisher)
    if not books:
        raise HTTPException(status_code=404, detail="Books matching filter not found")
    return books


@app.get("/books/{id}", response_model=BookSchema)
def fetch_single_book(id: int, db: Session = Depends(get_db)):
    book = get_book(db, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books/borrow/{id}")
def borrow_book_item(
    id: int, borrow_request: BorrowSchema, db: Session = Depends(get_db)
):
    book = borrow_book(**borrow_request.model_dump(), db=db)
    if not book or not book.is_available:
        raise HTTPException(status_code=404, detail="Book not available for borrowing")
    return {"message": "Book borrowed successfully"}


if __name__ == "__main__":
    import uvicorn

    port = 8001
    print(f"Starting frontend server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
