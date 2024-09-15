# Library Management System - API Services

This project consists of two independent API services to manage a library. The application allows users to browse through a catalog of books and borrow them. The project is structured into two separate APIs: one for frontend users and another for backend admin operations.

## API Services Overview

### 1. Frontend API
The Frontend API is used by users to interact with the library catalog and borrow books.

**Endpoints:**
- **Enroll Users**: Enroll users into the library using their email, first name, and last name.
- **List Available Books**: Retrieve a list of all available books in the library.
- **Get Book by ID**: Fetch details of a specific book using its ID.
- **Filter Books**:
  - By publisher (e.g., Wiley, Apress, Manning)
  - By category (e.g., fiction, technology, science)
- **Borrow Books**: Borrow books by ID and specify the number of days for which the book is borrowed.

### 2. Backend/Admin API
The Backend/Admin API is used by an admin to manage the library catalog and view user activities.

**Endpoints:**
- **Add New Books**: Add new books to the catalog.
- **Remove Book**: Remove a book from the catalog.
- **Fetch/List Users**: Retrieve a list of all users enrolled in the library.
- **Fetch/List User Borrowing Activities**: Retrieve a list of users and the books they have borrowed.
- **Fetch/List Unavailable Books**: Retrieve a list of books that are not available for borrowing, including the date they will be available.

## Requirements

- The endpoints need not be authenticated.
- The API can be built using any Python framework.
- Design the models as you deem fit.
- A book that has been lent out should no longer be available in the catalog.
- The two services should use different data stores.
- Implement a way to communicate changes between the two services (e.g., when the admin adds a book via the Backend API, the Frontend API should be updated with the latest book information).
- The project should be deployed using Docker contai
