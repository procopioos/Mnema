import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateNameError
from app.models.tag import Tag
from app.models.workspace import Workspace


def visible_to(tag: Tag, user_id: uuid.UUID) -> bool:
    """Global tags are visible to everyone; user tags only to their owner."""
    return tag.user_id is None or tag.user_id == user_id


def can_modify(tag: Tag, user_id: uuid.UUID) -> bool:
    """Global tags can be edited by any member; user tags only by their owner."""
    return visible_to(tag, user_id)


async def _name_taken(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    owner_id: uuid.UUID | None,
    name: str,
    exclude_tag_id: uuid.UUID | None = None,
) -> bool:
    conditions = [
        Tag.workspace_id == workspace_id,
        Tag.name == name,
        Tag.user_id.is_(None) if owner_id is None else Tag.user_id == owner_id,
    ]
    if exclude_tag_id is not None:
        conditions.append(Tag.id != exclude_tag_id)
    return await db.scalar(select(Tag.id).where(*conditions).limit(1)) is not None


async def create_tag(
    db: AsyncSession,
    workspace: Workspace,
    user_id: uuid.UUID,
    *,
    name: str,
    color: str,
    scope: str,
) -> Tag:
    owner_id = user_id if scope == "user" else None
    name = name.strip()
    if await _name_taken(db, workspace.id, owner_id, name):
        scope_label = "personal tag" if owner_id else "workspace tag"
        raise DuplicateNameError(f"You already have a {scope_label} named '{name}'")
    tag = Tag(workspace_id=workspace.id, user_id=owner_id, name=name, color=color)
    db.add(tag)
    await db.flush()
    await db.commit()
    return tag


async def update_tag(
    db: AsyncSession,
    tag: Tag,
    *,
    name: str | None = None,
    color: str | None = None,
) -> Tag:
    if name is not None:
        new_name = name.strip()
        if new_name != tag.name:
            if await _name_taken(db, tag.workspace_id, tag.user_id, new_name, exclude_tag_id=tag.id):
                raise DuplicateNameError(f"You already have a tag named '{new_name}'")
            tag.name = new_name
    if color is not None:
        tag.color = color
    await db.flush()
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.delete(tag)
    await db.flush()
    await db.commit()


async def list_visible_tags(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[Tag]:
    rows = await db.scalars(
        select(Tag)
        .where(
            Tag.workspace_id == workspace_id,
            or_(Tag.user_id.is_(None), Tag.user_id == user_id),
        )
        .order_by(Tag.name)
    )
    return list(rows)
