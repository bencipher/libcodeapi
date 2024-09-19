import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
# Update the database URL to use PostgreSQL


engine = create_engine(os.getenv("SQLALCHEMY_DATABASE_URL"))
# Remove the SQLite-specific connect_args
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
