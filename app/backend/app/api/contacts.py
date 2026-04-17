from typing import Optional
import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.contact import Contact, ContactList, ContactListMember
from app.models.enums import ContactEnrichmentStatus, ContactSource
from app.schemas.contacts import (
    ContactCreate,
    ContactListCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
    PaginatedContacts,
)
from app.utils.response import model_to_response

logger = get_logger("api.contacts")
router = APIRouter(prefix="/contacts", tags=["contacts"])
list_router = APIRouter(prefix="/contact-lists", tags=["contact-lists"])


def _contact_response(c: Contact) -> ContactResponse:
    return model_to_response(c, ContactResponse, exclude={"is_deleted", "last_inbound_whatsapp_at", "avatar_url", "timezone"},
        tags=c.tags or [], custom_fields=c.custom_fields or {},
        is_decision_maker=c.is_decision_maker or False,
        do_not_contact=c.do_not_contact or False,
        total_interactions=c.total_interactions or 0,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    contact = Contact(
        tenant_id=tenant_id,
        salutation=body.salutation,
        name=body.name, email=body.email, secondary_email=body.secondary_email,
        phone=body.phone, secondary_phone=body.secondary_phone,
        whatsapp_number=body.whatsapp_number or body.phone,
        country=body.country, city=body.city,
        company_name=body.company_name, company_id=body.company_id,
        title=body.title, department=body.department,
        is_decision_maker=body.is_decision_maker,
        preferred_language=body.preferred_language,
        preferred_channel=body.preferred_channel,
        do_not_contact=body.do_not_contact,
        linkedin_url=body.linkedin_url,
        tags=body.tags, custom_fields=body.custom_fields,
        opted_in_whatsapp=body.opted_in_whatsapp, opted_in_email=body.opted_in_email,
        source=ContactSource(body.source) if body.source in [s.value for s in ContactSource] else ContactSource.manual,
        notes=body.notes,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    logger.info("Contact created: id=%s tenant=%s", contact.id, tenant_id)
    return _contact_response(contact)


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_contacts(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Import contacts from CSV. Deduplicates by email and phone within tenant."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created_count = 0
    skipped_count = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        email = row.get("email", "").strip() or None
        phone = row.get("phone", "").strip() or None

        if not name:
            errors.append({"row": row_num, "error": "Missing name"})
            continue

        # Deduplicate
        if email:
            existing = await db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == email,
                    Contact.is_deleted.is_(False),
                )
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

        if phone:
            existing = await db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.phone == phone,
                    Contact.is_deleted.is_(False),
                )
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

        contact = Contact(
            tenant_id=tenant_id,
            name=name,
            email=email,
            phone=phone,
            company_name=row.get("company", "").strip() or None,
            title=row.get("title", "").strip() or None,
            tags=row.get("tags", "").split(",") if row.get("tags") else [],
            source=ContactSource.import_,
        )
        db.add(contact)
        created_count += 1

    await db.commit()
    logger.info("CSV import: tenant=%s created=%d skipped=%d errors=%d", tenant_id, created_count, skipped_count, len(errors))

    return {
        "created": created_count,
        "skipped": skipped_count,
        "errors": errors[:20],  # limit error details
    }


@router.get("", response_model=PaginatedContacts)
async def list_contacts(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    company: Optional[str] = None,
    enrichment_status: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    query = select(Contact).where(
        Contact.tenant_id == tenant_id,
        Contact.is_deleted.is_(False),
    )

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Contact.name.ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.company_name.ilike(search_term),
            )
        )

    if company:
        query = query.where(Contact.company_name.ilike(f"%{company}%"))

    if enrichment_status:
        query = query.where(Contact.enrichment_status == enrichment_status)

    if source:
        query = query.where(Contact.source == source)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    sort_col = getattr(Contact, sort_by, Contact.created_at)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    contacts = result.scalars().all()

    return PaginatedContacts(
        items=[_contact_response(c) for c in contacts],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
            Contact.is_deleted.is_(False),
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return _contact_response(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
            Contact.is_deleted.is_(False),
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await db.commit()
    await db.refresh(contact)
    logger.info("Contact updated: id=%s tenant=%s", contact_id, tenant_id)
    return _contact_response(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.is_deleted = True
    await db.commit()
    logger.info("Contact soft-deleted: id=%s tenant=%s", contact_id, tenant_id)


# --- Contact Lists ---


@list_router.post("", response_model=ContactListResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_list(
    body: ContactListCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    cl = ContactList(tenant_id=tenant_id, name=body.name, description=body.description)
    db.add(cl)
    await db.commit()
    await db.refresh(cl)
    logger.info("Contact list created: id=%s tenant=%s", cl.id, tenant_id)
    return ContactListResponse(
        id=str(cl.id), tenant_id=str(cl.tenant_id),
        name=cl.name, description=cl.description,
        member_count=0, created_at=cl.created_at.isoformat(),
    )


@list_router.get("", response_model=list)
async def list_contact_lists(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ContactList).where(ContactList.tenant_id == tenant_id)
    )
    lists = result.scalars().all()
    responses = []
    for cl in lists:
        count_result = await db.execute(
            select(func.count()).where(ContactListMember.contact_list_id == cl.id)
        )
        count = count_result.scalar() or 0
        responses.append(ContactListResponse(
            id=str(cl.id), tenant_id=str(cl.tenant_id),
            name=cl.name, description=cl.description,
            member_count=count, created_at=cl.created_at.isoformat(),
        ))
    return responses


@list_router.post("/{list_id}/contacts", status_code=status.HTTP_201_CREATED)
async def add_contacts_to_list(
    list_id: uuid.UUID,
    contact_ids: list[uuid.UUID],
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    # Verify list belongs to tenant
    cl_result = await db.execute(
        select(ContactList).where(ContactList.id == list_id, ContactList.tenant_id == tenant_id)
    )
    if not cl_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact list not found")

    added = 0
    for cid in contact_ids:
        # Check not already in list
        existing = await db.execute(
            select(ContactListMember).where(
                ContactListMember.contact_list_id == list_id,
                ContactListMember.contact_id == cid,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(ContactListMember(contact_list_id=list_id, contact_id=cid))
            added += 1

    await db.commit()
    logger.info("Added %d contacts to list=%s", added, list_id)
    return {"added": added}


@list_router.get("/{list_id}/contacts", response_model=list)
async def get_list_contacts(
    list_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    cl_result = await db.execute(
        select(ContactList).where(ContactList.id == list_id, ContactList.tenant_id == tenant_id)
    )
    if not cl_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact list not found")

    result = await db.execute(
        select(Contact)
        .join(ContactListMember, ContactListMember.contact_id == Contact.id)
        .where(
            ContactListMember.contact_list_id == list_id,
            Contact.is_deleted.is_(False),
        )
    )
    contacts = result.scalars().all()
    return [_contact_response(c) for c in contacts]
