from sqlalchemy.orm import Session
from . import models, schemas, auth

def get_user_by_email(db: Session, email: str):
    """Fetches a user from the DB by their email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Creates a new user in the DB."""
    # Hash the password before saving
    hashed_password = auth.get_password_hash(user.password)
    # Create a new User model instance
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password, 
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user