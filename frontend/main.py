import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from frontend.crud import (
    borrow_book,
    create_user_record,
    filter_books,
    get_book,
)
from exceptions.exceptions import add_exception_handlers
from frontend.schemas import (
    BookFilterParams,
    BookSchema,
    BorrowRequestSchema,
    BorrowSchema,
    UserCreate,
    UserSchema,
)
from frontend.storage import SessionLocal
from frontend.internal_message import setup_messaging, cleanup_messaging

from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.testing = app.state.testing if hasattr(app.state, "testing") else False

    if not app.state.testing:
        await setup_messaging(app)
    yield
    if not app.state.testing:
        await cleanup_messaging(app)

app = FastAPI(
    title="Library API",
    lifespan=lifespan,
    description="Frontend Required Endpoints for Library App for Cowrywise",
    version="1.0.0",
)

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
        logger.error(msg=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/books/", response_model=List[BookSchema], status_code=status.HTTP_200_OK)
def list_books(db: Session = Depends(get_db)):
    books = filter_books(db)
    if books is None:
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching books"
        )
    if not books:
        raise HTTPException(status_code=404, detail="No books found")
    return books


@app.get("/books/filter", response_model=List[BookSchema])
def filter_book_records(
    params: BookFilterParams = Depends(), db: Session = Depends(get_db)
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


@app.post("/books/borrow/", response_model=BorrowSchema, status_code=status.HTTP_200_OK)
def borrow_book_item(
    borrow_request: BorrowRequestSchema, db: Session = Depends(get_db)
):
    borrow_task = borrow_book(db, borrow_request)
    if not borrow_task:
        raise HTTPException(
            status_code=403, detail="Book cannot be borrowed, please verify details"
        )
    return borrow_task


if __name__ == "__main__":
    import uvicorn

    port = os.getenv("FRONTEND_PORT")
    print(f"Starting frontend server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
