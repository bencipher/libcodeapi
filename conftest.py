import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from frontend.main import app, get_db
from frontend.models import Base
from frontend.crud import create_user_record, create_book
from frontend.schemas import UserCreate, BookCreate
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from pytest_rabbitmq import factories

rabbitmq_my_proc = factories.rabbitmq_proc(port=None, logsdir="/tmp")
# rabbitmq_my = factories.rabbitmq('rabbitmq_my_proc')

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

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


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    app.state.testing = True
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.state.testing = False
    app.dependency_overrides.clear()


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


# backend fixtures

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:27017")


@pytest.fixture(scope="session")
async def mongo_client():
    client = AsyncIOMotorClient(MONGODB_URL)
    try:
        # The ismaster command is cheap and does not require auth.
        await client.admin.command("ismaster")
    except ConnectionFailure:
        pytest.fail("Server not available")

    yield client

    # Close the connection after all tests are done
    client.close()


@pytest.fixture(scope="function")
async def test_db(mongo_client):
    db_name = "test_db"
    db = mongo_client.db_name
    yield db
    # Clean up the test database after each test function
    await mongo_client.drop_database(db_name)


@pytest.fixture(scope="function")
async def books_collection(test_db):
    collection = test_db["books"]
    yield collection
    # Clean up the collection after each test function
    await collection.delete_many({})


@pytest.fixture(scope="function")
async def users_collection(test_db):
    collection = test_db["users"]
    yield collection
    # Clean up the collection after each test function
    await collection.delete_many({})
