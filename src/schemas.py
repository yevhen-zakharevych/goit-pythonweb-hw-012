from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserModel(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(from_attributes=True)


class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    birthday: Optional[date] = None
    additional_info: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    pass


class ContactResponse(ContactBase):
    id: int

    class Config:
        orm_mode = True
