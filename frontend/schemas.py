from datetime import datetime
import json
from pydantic import BaseModel, Field
from typing import Any, Optional


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


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
    borrow_date: Optional[datetime] = None
    return_date: datetime = None
    book: Optional[BookSchema] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


def custom_json_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=DateTimeEncoder)


class UserSchema(UserBase):
    id: int
    is_active: bool
    borrows: list[BorrowSchema] = []

    class Config:
        from_attributes = True


class BookFilterParams(BaseModel):
    publisher: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)


class BookUnavailableSchema(BookSchema):
    expected_return_date: datetime | None
