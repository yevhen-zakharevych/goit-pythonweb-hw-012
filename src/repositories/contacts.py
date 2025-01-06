from sqlalchemy.ext.asyncio import AsyncSession
from src.db import Contact
from src.schemas import ContactCreate


class ContactRepository:
    def __init__(self, db: AsyncSession):
        """
        Initializes a new instance of the class.

        Parameters:
            db (Session): The database session to be used by the instance.
        """
        self.db = db

    def create_contact(self, contact_data: ContactCreate, user_id: int):
        """
        Creates a new contact in the database.

        Parameters:
            contact_data (ContactCreate): The data of the contact to be created.
            user_id (int): The ID of the user who owns the contact.

        Returns:
            Contact: The created contact.
        """
        new_contact = Contact(**contact_data.dict(), user_id=user_id)
        self.db.add(new_contact)
        self.db.commit()
        self.db.refresh(new_contact)
        return new_contact

    def get_contact_by_email(self, email: str, user_id: int):
        """
        Retrieves a contact by its email.

        Parameters:
            email (str): The email of the contact to retrieve.
            user_id (int): The ID of the user who owns the contact.

        Returns:
            Contact: The contact with the given email, or None if not found.
        """
        return self.db.query(Contact).filter(Contact.email == email, Contact.user_id == user_id).first()

    def get_contacts(
            self,
            name: str | None,
            email: str | None,
            user_id: int,
    ):
        """
        Retrieves contacts based on the provided parameters.

        Parameters:
            name (str): The name of the contact to retrieve.
            email (str): The email of the contact to retrieve.
            user_id (int): The ID of the user who owns the contact.

        Returns:
            List[Contact]: A list of contacts that match the provided parameters.
        """
        query = self.db.query(Contact).filter(Contact.user_id == user_id)

        if name:
            query = query.filter((Contact.first_name.ilike(f"%{name}%")) | (Contact.last_name.ilike(f"%{name}%")))
        if email:
            query = query.filter(Contact.email.ilike(f"%{email}%"))

        return query.all()

    def get_contact_by_id(self, contact_id: int, user_id: int):
        """
        Retrieves a contact by its ID.

        Parameters:
            contact_id (int): The ID of the contact to retrieve.
            user_id (int): The ID of the user who owns the contact.

        Returns:
            Contact: The contact with the given ID, or None if not found.
        """
        return self.db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()

    def get_contacts_by_user(self, user_id: int):
        """
        Retrieves all contacts for a given user.

        Parameters:
            user_id (int): The ID of the user who owns the contacts.

        Returns:
            List[Contact]: A list of all contacts for the given user.
        """
        return self.db.query(Contact).filter(Contact.user_id == user_id).all()

    def update_contact(self, contact_id: int, user_id: int, contact_data: dict):
        """
        Updates a contact in the database.

        Parameters:
            contact_id (int): The ID of the contact to update.
            user_id (int): The ID of the user who owns the contact.
            contact_data (dict): The updated data of the contact.

        Returns:
            Contact: The updated contact.
        """
        contact = self.get_contact_by_id(contact_id, user_id)
        if contact:
            for key, value in contact_data.items():
                setattr(contact, key, value)
            self.db.commit()
            self.db.refresh(contact)
        return contact

    def delete_contact(self, contact_id: int, user_id: int):
        """
        Deletes a contact from the database.

        Parameters:
            contact_id (int): The ID of the contact to delete.
            user_id (int): The ID of the user who owns the contact.

        Returns:
            dict: A dictionary containing a message indicating the success of the operation.
        """
        contact = self.get_contact_by_id(contact_id, user_id)
        if contact:
            self.db.delete(contact)
            self.db.commit()
            return {"detail": "Contact deleted successfully."}
        return {"detail": "Contact not found."}

    def get_birthdays(self, user_id: int, start_date, end_date):
        """
        Retrieves all contacts that have a birthday between the start date and end date.

        Parameters:
            user_id (int): The ID of the user who owns the contacts.
            start_date (date): The start date of the range of birthdays.
            end_date (date): The end date of the range of birthdays.

        Returns:
            List[Contact]: A list of all contacts that have a birthday between the start date and end date.
        """
        contacts = (
            self.db.query(Contact)
            .filter(Contact.user_id == user_id, Contact.birthday >= start_date, Contact.birthday <= end_date)
            .all()
        )
        return contacts
