from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from frontend.storage import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    publisher = Column(String, nullable=False)
    category = Column(String, nullable=False)
    is_available = Column(Boolean, default=True)
    borrowed_until = Column(DateTime, nullable=True)

    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    borrower = relationship("User", back_populates="borrowed_books")


class Borrow(Base):
    __tablename__ = "borrows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    borrow_date = Column(DateTime, default=datetime.utcnow)
    return_date = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="borrows")
    book = relationship("Book", back_populates="borrows")


User.borrowed_books = relationship("Book", back_populates="borrower")
User.borrows = relationship("Borrow", back_populates="user")
Book.borrows = relationship("Borrow", back_populates="book")
