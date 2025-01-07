import pytest
from unittest.mock import AsyncMock, MagicMock
from src.db import Contact
from src.schemas import ContactCreate
from src.repositories.contacts import ContactRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def contact_data():
    return ContactCreate(first_name="John", last_name="Doe", email="john.doe@example.com", phone="1234567890", birthday="1990-01-01")


@pytest.fixture
def mock_contact():
    return Contact(id=1, first_name="John", last_name="Doe", email="john.doe@example.com", phone="1234567890", user_id=1)


@pytest.mark.asyncio
async def test_create_contact(contact_repository, mock_session, contact_data):
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock()

    contact = contact_repository.create_contact(contact_data, user_id=1)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    assert contact.user_id == 1
    assert contact.first_name == "John"


@pytest.mark.asyncio
async def test_get_contact_by_email(contact_repository, mock_session, mock_contact):
    mock_session.query = MagicMock()
    mock_session.query().filter().first.return_value = mock_contact

    contact = contact_repository.get_contact_by_email(email="john.doe@example.com", user_id=1)

    assert contact.email == "john.doe@example.com"
    assert contact.user_id == 1


@pytest.mark.asyncio
async def test_get_contacts(contact_repository, mock_session, mock_contact):
    mock_session.query = MagicMock()
    mock_session.query().filter().all.return_value = [mock_contact]

    contacts = contact_repository.get_contacts(None, None, user_id=1)

    assert len(contacts) == 1
    assert contacts[0].first_name == "John"


@pytest.mark.asyncio
async def test_update_contact(contact_repository, mock_session, mock_contact):
    mock_session.query = MagicMock()
    mock_session.query().filter().first.return_value = mock_contact
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock()

    updated_contact = contact_repository.update_contact(contact_id=1, user_id=1, contact_data={"email": "new.email@example.com"})

    assert updated_contact.email == "new.email@example.com"
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_delete_contact(contact_repository, mock_session, mock_contact):
    mock_session.query = MagicMock()
    mock_session.query().filter().first.return_value = mock_contact
    mock_session.delete = MagicMock()
    mock_session.commit = MagicMock()

    result = contact_repository.delete_contact(contact_id=1, user_id=1)

    mock_session.delete.assert_called_once_with(mock_contact)
    mock_session.commit.assert_called_once()
    assert result == {"detail": "Contact deleted successfully."}


@pytest.mark.asyncio
async def test_get_birthdays(contact_repository, mock_session, mock_contact):
    mock_session.query = MagicMock()
    mock_session.query().filter().all.return_value = [mock_contact]

    contacts = contact_repository.get_birthdays(user_id=1, start_date="2025-01-01", end_date="2025-12-31")

    assert len(contacts) == 1
    assert contacts[0].first_name == "John"
