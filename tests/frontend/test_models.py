import pytest
from sqlalchemy.orm import Session

from datetime import datetime, timedelta

from frontend.models import Borrow, User, Book


def test_user_model(db_session: Session, test_user: User):
    assert test_user.email == "test@example.com"
    assert test_user.first_name == "Test"
    assert test_user.last_name == "User"
    assert test_user.hashed_password != "testpassword"


def test_book_model(db_session: Session, test_book: Book):
    assert test_book.title == "Test Book"
    assert test_book.publisher == "Test Publisher"
    assert test_book.isbn == "1234567890"
    assert test_book.is_available == True


def test_borrow_model(db_session: Session, test_user: User, test_book: Book):
    borrow_date = datetime.utcnow()
    return_date = borrow_date + timedelta(days=7)

    borrow = Borrow(
        user_id=test_user.id,
        book_id=test_book.id,
        borrow_date=borrow_date,
        return_date=return_date,
    )

    db_session.add(borrow)
    db_session.commit()
    db_session.refresh(borrow)

    assert borrow.user_id == test_user.id
    assert borrow.book_id == test_book.id
    assert borrow.borrow_date == borrow_date
    assert borrow.return_date == return_date


def test_user_book_relationship(db_session: Session, test_user: User, test_book: Book):
    borrow_date = datetime.utcnow()
    return_date = borrow_date + timedelta(days=7)

    borrow = Borrow(
        user_id=test_user.id,
        book_id=test_book.id,
        borrow_date=borrow_date,
        return_date=return_date,
    )

    db_session.add(borrow)
    db_session.commit()
    db_session.refresh(test_user)
    db_session.refresh(test_book)

    assert len(test_user.borrows) == 1
    assert test_user.borrows[0].book_id == test_book.id
    assert len(test_book.borrows) == 1
    assert test_book.borrows[0].user_id == test_user.id
