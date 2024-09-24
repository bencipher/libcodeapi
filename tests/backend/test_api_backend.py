import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app, get_db


@pytest.fixture(scope="session")
def test_app():
    app.state.testing = True
    app.dependency_overrides[get_db] = MagicMock()
    app.state.rabbitmq_connection = MagicMock()
    app.state.rabbitmq_channel = MagicMock()
    return TestClient(app)


@pytest.mark.skip()
@pytest.mark.asyncio
@patch("backend.main.create_book", new_callable=AsyncMock)
@patch(
    "backend.main.app.state.rabbitmq_channel.default_exchange.publish",
    new_callable=AsyncMock,
)
async def test_add_book(mock_publish, mock_create_book, test_app):
    mock_create_book.return_value = {
        "id": "test_id",
        "title": "Chronicles of the kings",
    }

    book_data = {
        "title": "Chronicles of the kings",
        "author": "Solomon Jesse",
        "isbn": "8912937819",
        "publisher": "Moses & Co",
        "category": "Religious",
        "total_copies": 9,
        "description": "A bible book illustrating the history of the Israelites",
    }

    # Use the test client to send a POST request
    response = test_app.post("/books", json=book_data)

    # Ensure the response status code is 201
    assert response.status_code == 201

    # Ensure the response JSON contains the expected book ID
    response_data = response.json()
    assert response_data == "test_id"

    # Ensure the create_book function was called once
    mock_create_book.assert_called_once()

    # Ensure the publish function was called once
    mock_publish.assert_called_once()


@pytest.mark.skip()
@pytest.mark.asyncio
@patch("backend.main.get_book", new_callable=AsyncMock)
async def test_read_book(mock_get_book, test_app):
    mock_get_book.return_value = {"id": "test_id", "title": "Test Book"}

    book_id = "test_id"
    response = test_app.get(f"/books/{book_id}")
    # assert response.status_code == 200
    book = response.json()
    assert book["id"] == book_id

    mock_get_book.assert_called_once_with(test_app.app.state.db, book_id)


@pytest.mark.skip()
@pytest.mark.asyncio
@patch("backend.main.update_book", new_callable=AsyncMock)
async def test_modify_book(mock_update_book, test_app):
    mock_update_book.return_value = {"id": "test_id", "title": "Updated Test Book"}

    book_id = "test_id"
    book_update = {
        "title": "Updated Test Book",
        "author": "Updated Test Author",
        "isbn": "0987654321",
        "published_date": "2023-01-02",
        "total_copies": 5,
    }
    response = test_app.put(f"/books/{book_id}", json=book_update)
    # assert response.status_code == 200
    updated_book = response.json()
    assert updated_book["title"] == "Updated Test Book"

    mock_update_book.assert_called_once_with(
        test_app.app.state.db, book_id, book_update
    )


@pytest.mark.skip()
@pytest.mark.asyncio
@patch("backend.main.delete_book", new_callable=AsyncMock)
@patch("backend.main.get_book", new_callable=AsyncMock)
@patch(
    "backend.main.app.state.rabbitmq_channel.default_exchange.publish",
    new_callable=AsyncMock,
)
async def test_remove_book(mock_publish, mock_get_book, mock_delete_book, test_app):
    mock_get_book.return_value = {"id": "test_id", "isbn": "1234567890"}
    mock_delete_book.return_value = True

    book_id = "test_id"
    response = test_app.delete(f"/books/{book_id}")
    # assert response.status_code == 200
    result = response.json()
    assert (
        result["message"]
        == "Book successfully deleted from backend and delete message sent to frontend"
    )

    mock_get_book.assert_called_once_with(test_app.app.state.db, book_id)
    mock_delete_book.assert_called_once_with(test_app.app.state.db, book_id)
    mock_publish.assert_called_once()


@pytest.mark.skip()
@pytest.mark.asyncio
@patch(
    "backend.main.app.state.rabbitmq_channel.default_exchange.publish",
    new_callable=AsyncMock,
)
async def test_list_users(mock_publish, test_app):
    mock_publish.return_value = None

    response = test_app.get("/users")
    # assert response.status_code == 200

    mock_publish.assert_called_once()


@pytest.mark.skip()
@pytest.mark.asyncio
@patch(
    "backend.main.app.state.rabbitmq_channel.default_exchange.publish",
    new_callable=AsyncMock,
)
async def test_list_users_with_borrowed_books(mock_publish, test_app):
    mock_publish.return_value = None

    response = test_app.get("/users/borrowed-books/")
    # assert response.status_code == 200

    mock_publish.assert_called_once()


@pytest.mark.skip()
@pytest.mark.asyncio
@patch(
    "backend.main.app.state.rabbitmq_channel.default_exchange.publish",
    new_callable=AsyncMock,
)
async def test_list_unavailable_books(mock_publish, test_app):
    mock_publish.return_value = None

    response = test_app.get("/unavailable-books")
    # assert response.status_code == 200

    mock_publish.assert_called_once()
