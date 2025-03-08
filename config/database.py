from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.env import Env


# Create the SQLAlchemy engine with connection pooling settings
engine = create_engine(
    Env.DATABASE_URL,
    pool_size=5,         # Number of permanent connections in the pool
    max_overflow=10,     # Number of extra connections allowed when pool is full
    pool_timeout=30,     # Timeout in seconds for getting a connection from the pool
    echo=True            # Set to True for SQL output logging during debugging
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = sessionmaker(bind=engine)

# Declare the base class for models
Base = declarative_base()