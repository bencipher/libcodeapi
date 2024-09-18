from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import bcrypt

from frontend import models, schemas
from frontend.exceptions import (
    BookNotAvailableError,
    BookNotFoundError,
    UserNotFoundError,
    DatabaseError,
)

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def filter_books(
    db: Session,
    category: Optional[str] = None,
    publisher: Optional[str] = None,
    availability: Optional[bool] = True,
) -> List[models.Book]:
    try:
        query = db.query(models.Book)
        if category:
            query = query.filter(models.Book.category.ilike(f"%{category}%"))
        if publisher:
            query = query.filter(models.Book.publisher.ilike(f"%{publisher}%"))
        if availability is not None:
            query = query.filter(models.Book.is_available == availability)
        return query.all()
    except SQLAlchemyError as e:
        raise DatabaseError("filter", str(e))


def get_user_by_id(db: Session, user_id: int):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            raise UserNotFoundError(user_id)
        return user
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))


def get_user_by_email(db: Session, email: str):
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user is None:
            raise UserNotFoundError(email)
        return user
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))


def get_users(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(models.User).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))


def create_user_record(db: Session, user: schemas.UserCreate):
    try:
        hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())
        db_user = models.User(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            hashed_password=hashed_password.decode("utf-8"),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except SQLAlchemyError as e:
        db.rollback()
        raise DatabaseError("create", str(e))


def create_book(db: Session, item: schemas.BookCreate):
    try:
        db_item = models.Book(**item.model_dump())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except SQLAlchemyError as e:
        db.rollback()
        raise DatabaseError("create", str(e))


def get_book(db: Session, book_id: int):
    try:
        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if book is None:
            raise BookNotFoundError(book_id)
        return book
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))


def borrow_book(db: Session, book_request: schemas.BorrowRequestSchema):
    try:
        book = get_book(db, book_request.book_id)
        if not book.is_available:
            raise BookNotAvailableError(book_request.book_id)

        user = get_user_by_id(db, book_request.user_id)

        borrow_date = datetime.now(timezone.utc)
        return_date = borrow_date + timedelta(days=book_request.num_of_days)

        borrow = models.Borrow(
            user_id=book_request.user_id,
            book_id=book_request.book_id,
            borrow_date=borrow_date,
            return_date=return_date,
        )

        book.is_available = False
        book.borrower_id = book_request.user_id

        db.add(borrow)
        db.commit()
        db.refresh(borrow)
        db.refresh(book)

        return borrow
    except SQLAlchemyError as e:
        db.rollback()
        raise DatabaseError("borrow", str(e))


def delete_book_by_isbn(db: Session, isbn: str):
    try:
        book = db.query(models.Book).filter(models.Book.isbn == isbn).first()
        if not book:
            raise BookNotFoundError(isbn)
        db.delete(book)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise DatabaseError("delete", str(e))


def get_users_and_borrowed_books(db: Session, skip: int = 0, limit: int = 100):
    try:
        return (
            db.query(models.User)
            .options(selectinload(models.User.borrows).selectinload(models.Borrow.book))
            .distinct()
            .offset(skip)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))


def get_unavailable_books_with_return_dates(db: Session):
    try:
        return (
            db.query(models.Book)
            .filter(models.Book.is_available == False)
            .options(selectinload(models.Book.borrows))
            .all()
        )
    except SQLAlchemyError as e:
        raise DatabaseError("fetch", str(e))
