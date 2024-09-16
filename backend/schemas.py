from pydantic import BaseModel
from typing import Optional, List


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    publisher: str
    category: str
    total_copies: int
    description: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    total_copies: Optional[int] = None


class UserCreate(BaseModel):
    name: str
    email: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    borrowed_books: Optional[List[str]] = None
