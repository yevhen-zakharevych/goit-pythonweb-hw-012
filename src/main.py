import os
import json

from datetime import date, timedelta
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException, Depends, status, BackgroundTasks, Request, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis

from src.services.auth import create_access_token, get_current_user, Hash, get_email_from_token
from src.db import Base, engine, get_db, User
from src.schemas import ContactCreate, ContactUpdate, ContactResponse, UserModel
from src.services.email import send_email
from src.services.upload_file import UploadFileService
from src.repositories.contacts import ContactRepository
from dotenv import load_dotenv

load_dotenv()

CLD_NAME = os.environ.get("CLOUDINARY_NAME")
CLD_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLD_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

app = FastAPI()
hash_handler = Hash()
limiter = Limiter(key_func=get_remote_address)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

origins = [
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.post("/signup")
async def signup(
        body: UserModel,
        background_tasks: BackgroundTasks,
        request: Request,
        db: Session = Depends(get_db)):
    """
    Create a new user
    """
    exist_user = db.execute(select(User).filter(User.username == body.username))
    exist_user = exist_user.scalars().first()
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )
    new_user = User(
        username=body.username, password=hash_handler.get_password_hash(body.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(
        send_email, new_user.username, new_user.username, request.base_url
    )

    return {"new_user": new_user.username}


@app.post("/login")
async def login(
    body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login user
    """
    result = db.execute(select(User).filter(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username"
        )
    if not hash_handler.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Emai is not confirmed. Please, check your email",
        )
    # Generate JWT
    access_token = await create_access_token(data={"sub": user.username})
    user_out = UserModel.from_orm(user)

    print(access_token)

    r.setex(access_token, 3600, user_out.json())

    return {"access_token": access_token, "token_type": "bearer"}


@app.post(
    "/contacts/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(
        contact: ContactCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new contact
    """
    contact_repo = ContactRepository(db)
    new_contact = contact_repo.create_contact(contact, user_id=current_user.id)
    return new_contact


@app.get("/contacts/", response_model=List[ContactResponse])
def read_contacts(
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get contacts
    """
    contact_repo = ContactRepository(db)
    return contact_repo.get_contacts(name, email, current_user.id)


@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get contact
    """
    contact_repo = ContactRepository(db)
    contact = contact_repo.get_contact_by_id(contact_id, current_user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return contact


@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
        contact_id: int, contact: ContactUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update contact
    """
    contact_repo = ContactRepository(db)
    return contact_repo.update_contact(contact_id, current_user.id, contact.dict(exclude_unset=True))


@app.delete("/contacts/{contact_id}", response_model=dict)
def delete_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete contact
    """
    contact_repo = ContactRepository(db)
    return contact_repo.delete_contact(contact_id, current_user.id)


@app.get("/contacts/upcoming-birthdays/", response_model=List[ContactResponse], )
def upcoming_birthdays(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get upcoming birthdays
    """
    today = date.today()
    next_week = today + timedelta(days=7)
    contacts_repo = ContactRepository(db)
    contacts = contacts_repo.get_birthdays(current_user.id, today, next_week)
    return contacts


@app.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: Session = Depends(get_db)):
    """
    Confirm email
    """
    email = await get_email_from_token(token)

    user = db.query(User).filter(User.username == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    setattr(user, "confirmed", True)
    db.commit()

    return {"message": "Your email is confirmed"}


@app.patch("/avatar")
async def update_avatar_user(
    file: UploadFile = File(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update avatar user
    """
    avatar_url = UploadFileService(
        CLD_NAME, CLD_API_KEY, CLD_API_SECRET
    ).upload_file(file, current_user.username)

    edited_user = db.query(User).filter(User.username == current_user.username).first()
    edited_user.avatar_url = avatar_url

    db.commit()

    return {"message": "Avatar updated successfully", "avatar_url": avatar_url}


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Rate limit handler
    """
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please try again later."},
    )


@app.get("/me")
@limiter.limit("5/minute")
async def my_endpoint(request: Request):
    """
    My endpoint
    """
    return {"message": "The route with limitations."}


@app.get("/protected-route")
async def protected_route(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Example protected route that retrieves the user from Redis or the database.
    """
    cached_user = r.get(token)

    if cached_user:
        return {"message": f"Hello, {json.loads(cached_user)['username']}!"}

    user = db.query(User).filter(User.username == current_user.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"message": f"Hello, {user.username}!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
