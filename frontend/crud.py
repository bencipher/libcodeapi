from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import bcrypt

from frontend import models, schemas

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def get_books(db: Session) -> Optional[List[models.Book]]:
    try:
        books = db.query(models.Book).all()
        return books
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred while fetching books: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error occurred while fetching books: {str(e)}")
        return None


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user_record(db: Session, user: schemas.UserCreate):
    # Hash the password
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


def create_book(db: Session, item: schemas.BookCreate):
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_book(db: Session, book_id: int):
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def filter_books(
    db: Session, category: Optional[str] = None, publisher: Optional[str] = None
):
    query = db.query(models.Book)
    if category:
        query = query.filter(models.Book.category.ilike(f"%{category}%"))
    if publisher:
        query = query.filter(models.Book.publisher.ilike(f"%{publisher}%"))
    return query.all()


def borrow_book(db: Session, book_id: int, user_id: int, days: int):
    book = get_book(db, book_id)
    if not book or not book.is_available:
        return None

    borrow_date = datetime.now(timezone.utc)
    return_date = borrow_date + timedelta(days=days)

    borrow = models.Borrow(
        user_id=user_id,
        book_id=book_id,
        borrow_date=borrow_date,
        return_date=return_date,
    )

    book.is_available = False
    book.borrowed_until = return_date
    book.borrower_id = user_id

    db.add(borrow)
    db.commit()
    db.refresh(borrow)
    db.refresh(book)

    return borrow
