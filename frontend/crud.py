from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models, schemas


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user_record(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password)
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


def get_books(
    db: Session, skip: int = 0, limit: int = 100, available_only: bool = True
):
    query = db.query(models.Book)
    if available_only:
        query = query.filter(models.Book.is_available == True)
    return query.offset(skip).limit(limit).all()


def get_book(db: Session, book_id: int):
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def filter_books(
    db: Session,
    publisher: str = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Book)

    if publisher:
        query = query.filter(models.Book.publisher == publisher)

    if category:
        query = query.filter(models.Book.category == category)

    return query.offset(skip).limit(limit).all()


def borrow_book(db: Session, book_id: int, user_id: int, days: int):
    book = get_book(db, book_id)
    if not book or not book.is_available:
        return None

    borrow_date = datetime.utcnow()
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
