from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Update the database URL to use PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@db:5432/library"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
# Remove the SQLite-specific connect_args
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
