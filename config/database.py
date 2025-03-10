from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.env import Env

# Create the SQLAlchemy engine
engine = create_engine(
    Env.DATABASE_URL,
    pool_size=5, 
    max_overflow=10,
    pool_timeout=30,
    echo=True
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare the base class for models
Base = declarative_base()

# Optional: If you want to have a Session object to use in your models
Session = sessionmaker(bind=engine)
