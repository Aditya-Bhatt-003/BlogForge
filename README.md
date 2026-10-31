# BlogForge

A full-stack blogging platform built with **FastAPI**, **PostgreSQL**, and **SQLAlchemy**. BlogForge provides user authentication, post management, profile customization, image uploads, and password recovery.

**Live Demo:** https://blogforge-pmo4.onrender.com
**Source Code:** [GitHub Repository](https://github.com/Aditya-Bhatt-003/BlogForge)

---

## Overview

BlogForge is a web-based blogging application designed to provide a practical blogging experience while demonstrating modern backend development practices.

The application uses FastAPI for its backend, PostgreSQL for persistent data storage, and SQLAlchemy's asynchronous ORM for database operations. It also integrates AWS S3 for profile image storage and email services for password recovery.

## Features

* **User Authentication** – Secure registration and login using JWT-based authentication.
* **Password Security** – Password hashing using Argon2.
* **Blog Post Management** – Create, view, update, and delete blog posts.
* **Pagination** – Paginated post listings for improved navigation.
* **User Profiles** – User profile management and profile picture uploads.
* **Cloud Image Storage** – Profile images stored using Amazon S3.
* **Password Recovery** – Email-based password reset functionality.
* **Database Migrations** – Schema versioning and migrations using Alembic.
* **Automated Testing** – Application tests using Pytest.

## Technology Stack

| Category            | Technologies           |
| ------------------- | ---------------------- |
| Backend             | Python, FastAPI        |
| Database            | PostgreSQL             |
| ORM                 | SQLAlchemy 2.0 (Async) |
| Authentication      | JWT, Argon2            |
| Database Migrations | Alembic                |
| Image Processing    | Pillow                 |
| Cloud Storage       | AWS S3                 |
| Email Service       | SMTP, Mailtrap         |
| Testing             | Pytest, Moto           |
| Package Management  | uv                     |
| Deployment          | Render                 |

## Project Structure

```text
BlogForge/
│
├── alembic/                # Database migrations
├── routers/                # Application route handlers
├── static/                 # Static assets
├── templates/              # HTML templates
├── tests/                  # Automated tests
│
├── main.py                 # Application entry point
├── auth.py                 # Authentication utilities
├── config.py               # Application configuration
├── database.py             # Database connection and sessions
├── email_utils.py          # Email functionality
├── image_utils.py          # Image processing utilities
├── models.py               # SQLAlchemy database models
├── schema.py               # Pydantic schemas
│
├── alembic.ini             # Alembic configuration
├── pyproject.toml          # Project dependencies and metadata
├── uv.lock                 # Locked dependency versions
├── .gitignore
└── README.md
```

## Getting Started

Follow these instructions to run BlogForge locally.

### Prerequisites

Make sure you have the following installed:

* Python 3.12 or later
* PostgreSQL
* [uv](https://docs.astral.sh/uv/)

### 1. Clone the Repository

```bash
git clone https://github.com/Aditya-Bhatt-003/BlogForge.git
```

Navigate to the project directory:

```bash
cd BlogForge
```

### 2. Install Dependencies

Install the project dependencies using uv:

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory.

Add the following configuration:

```env
# Database
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/blogforge

# Authentication
SECRET_KEY=your_secret_key

# AWS S3
S3_BUCKET_NAME=your_bucket_name
S3_REGION=your_aws_region
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_access_key

# Email Configuration
MAIL_SERVER=your_smtp_server
MAIL_PORT=587
MAIL_USERNAME=your_email_username
MAIL_PASSWORD=your_email_password
MAIL_FROM=your_sender_email

# Frontend
FRONTEND_URL=http://localhost:8000
```

**Important:**

* Replace the placeholder values with your actual configuration.
* Generate a strong, unique `SECRET_KEY`.
* Configure an AWS S3 bucket and appropriate IAM permissions for image uploads.
* Configure SMTP credentials for password recovery emails.
* Never commit your `.env` file or expose credentials publicly.

### 4. Run Database Migrations

Apply the database migrations:

```bash
uv run alembic upgrade head
```

This creates or updates the database schema.

### 5. Start the Application

Run the development server:

```bash
uv run fastapi dev main.py
```

Open the application in your browser:

```text
http://127.0.0.1:8000
```

## Running Tests

Run the automated test suite using:

```bash
uv run pytest tests/ -v
```

## Database Migrations

BlogForge uses Alembic to manage database schema changes.

Apply existing migrations:

```bash
uv run alembic upgrade head
```

Create a new migration:

```bash
uv run alembic revision --autogenerate -m "describe your changes"
```

Review generated migration files before applying them.

## Deployment

BlogForge is deployed on **Render**.

The production deployment uses:

* Render for application hosting.
* Supabase PostgreSQL for database hosting.
* AWS S3 for profile image storage.
* SMTP for email functionality.

**Live Application:** [Visit BlogForge](https://blogforge-pmo4.onrender.com)

## Security Considerations

* Sensitive configuration is managed through environment variables.
* Passwords are hashed using Argon2.
* JWT tokens are used for authentication.
* Database schema changes are managed through migrations.
* Production credentials should never be committed to version control.

## Author

**Aditya Bhatt**

* GitHub: [Aditya-Bhatt-003](https://github.com/Aditya-Bhatt-003)

---

If you find this project useful, consider giving the repository a ⭐ on GitHub.
