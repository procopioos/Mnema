import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession, MemberWorkspace, TagResource
from app.schemas.tag import TagCreate, TagOut, TagUpdate
from app.services import tags as tags_service

router = APIRouter()


def _require_owner(tag_user_id: uuid.UUID | None, user_id: uuid.UUID) -> None:
    if tag_user_id is not None and tag_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Personal tags can only be managed by their owner",
        )


@router.get("/workspaces/{workspace_id}/tags", response_model=list[TagOut])
async def list_tags(workspace: MemberWorkspace, user: CurrentUser, db: DbSession) -> list[TagOut]:
    rows = await tags_service.list_visible_tags(db, workspace.id, user.id)
    return [TagOut.model_validate(tag) for tag in rows]


@router.post("/workspaces/{workspace_id}/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(workspace: MemberWorkspace, user: CurrentUser, payload: TagCreate, db: DbSession) -> TagOut:
    tag = await tags_service.create_tag(
        db,
        workspace,
        user.id,
        name=payload.name,
        color=payload.color,
        scope=payload.scope,
    )
    return TagOut.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def update_tag(tag: TagResource, user: CurrentUser, payload: TagUpdate, db: DbSession) -> TagOut:
    _require_owner(tag.user_id, user.id)
    updated = await tags_service.update_tag(
        db,
        tag,
        name=payload.name,
        color=payload.color,
    )
    return TagOut.model_validate(updated)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag: TagResource, user: CurrentUser, db: DbSession) -> None:
    _require_owner(tag.user_id, user.id)
    await tags_service.delete_tag(db, tag)
