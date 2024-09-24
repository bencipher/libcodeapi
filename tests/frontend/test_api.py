import pytest
from fastapi.testclient import TestClient
from frontend.main import app

client = TestClient(app)


def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "email": "newuser@example.com",
            "password": "newpassword",
            "first_name": "New",
            "last_name": "User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data


def test_get_books(client, test_book):
    response = client.get("/books/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == test_book.title


def test_filter_books(client, test_book):
    response = client.get("/books/filter", params={"category": "Test Category"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["category"] == "Test Category"


def test_get_single_book(client, test_book):
    response = client.get(f"/books/{test_book.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_book.title


def test_borrow_book(client, test_user, test_book):
    response = client.post(
        "/books/borrow/",
        json={"user_id": test_user.id, "book_id": test_book.id, "num_of_days": 7},
    )
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert "book_id" in data
    # assert data["message"] == "Book borrowed successfully"


def test_borrow_unavailable_book(client, test_user, test_book, db_session):
    # First, borrow the book
    client.post(
        "/books/borrow/",
        json={"user_id": test_user.id, "book_id": test_book.id, "num_of_days": 7},
    )

    # Try to borrow the same book again
    response = client.post(
        "/books/borrow/",
        json={"user_id": test_user.id, "book_id": test_book.id, "num_of_days": 7},
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "Error occured, check the details supplied" in data["detail"]
