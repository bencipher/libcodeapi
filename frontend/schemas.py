from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class BookBase(BaseModel):
    title: str
    publisher: str
    category: str
    description: str | None = None
    isbn: str


class BookCreate(BookBase):
    pass


class BookSchema(BookBase):
    id: int
    borrower_id: int | None = None
    is_available: bool
    borrowed_until: datetime | None = None  # to be removed

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str


class BorrowBase(BaseModel):
    user_id: int
    book_id: int


class BorrowRequestSchema(BorrowBase):
    num_of_days: int


class BorrowSchema(BorrowBase):
    id: int
    borrow_date: datetime
    return_date: datetime
    book: Optional[BookSchema] = None

    class Config:
        from_attributes = True


class UserSchema(UserBase):
    id: int
    is_active: bool
    borrows: list[BorrowSchema] = []

    class Config:
        from_attributes = True


class BookFilterParams(BaseModel):
    publisher: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
