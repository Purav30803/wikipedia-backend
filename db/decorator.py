from functools import wraps
from config.database import SessionLocal

def with_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            # Pass the db session as a keyword argument
            return func(*args, db=db, **kwargs)
        finally:
            db.close()
    return wrapper
