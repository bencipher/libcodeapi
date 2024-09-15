from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class BookBase(BaseModel):
    title: str
    publisher: str
    category: str
    description: str | None = None


class BookCreate(BookBase):
    pass


class BookSchema(BookBase):
    id: int
    borrower_id: int | None = None
    is_available: bool
    borrowed_until: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str


class UserSchema(UserBase):
    id: int
    is_active: bool
    borowed_books: list[BookSchema] = []

    class Config:
        from_attributes = True


class BorrowBase(BaseModel):
    user_id: int
    book_id: int
    borrow_date: datetime
    return_date: datetime


class BorrowCreate(BorrowBase):
    pass


class BorrowSchema(BorrowBase):
    id: int

    class Config:
        from_attributes = True


class BookFilterParams(BaseModel):
    publisher: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
