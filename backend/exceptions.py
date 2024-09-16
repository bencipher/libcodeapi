class BookNotFoundError(Exception):
    def __init__(self, book_id: str):
        self.message = f"Book with id {book_id} not found"
        super().__init__(self.message)


class UserNotFoundError(Exception):
    def __init__(self, user_id: str):
        self.message = f"User with id {user_id} not found"
        super().__init__(self.message)


class BookNotAvailableError(Exception):
    def __init__(self, book_id: str):
        self.message = f"Book with id {book_id} is not available"
        super().__init__(self.message)
