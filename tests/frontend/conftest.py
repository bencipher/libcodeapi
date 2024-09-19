import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from frontend.main import app, get_db
from frontend.models import Base
from frontend.crud import create_user_record, create_book
from frontend.schemas import UserCreate, BookCreate
from dotenv import load_dotenv

load_dotenv()

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DB_URL")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    app.state.testing = True

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.state.testing = False


@pytest.fixture(scope="function")
def test_user(db_session):
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword",
        first_name="Test",
        last_name="User",
    )
    user = create_user_record(db_session, user_data)
    return user


@pytest.fixture(scope="function")
def test_book(db_session):
    book_data = BookCreate(
        title="Test Book",
        isbn="1234567890",
        publisher="Test Publisher",
        category="Test Category",
        description="Test Description",
        is_available=True,
    )
    book = create_book(db_session, book_data)
    return book
