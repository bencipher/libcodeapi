from datetime import datetime
from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    publisher: str
    category: str
    description: str | None = None


class BookCreate(BookBase):
    pass


class BookSchema(BookBase):
    id: int
    borrower_id: int
    is_available: bool
    borrowed_until: datetime

    class Config:
        orm_mode = True


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
        orm_mode = True


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
        orm_mode = True
