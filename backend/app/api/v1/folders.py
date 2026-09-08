from fastapi import APIRouter, status

from app.core.deps import DbSession, FolderResource, MemberWorkspace
from app.schemas.folder import FolderCreate, FolderOut, FolderUpdate
from app.services import folders as folders_service

router = APIRouter()


@router.get("/workspaces/{workspace_id}/folders", response_model=list[FolderOut])
async def list_folders(workspace: MemberWorkspace, db: DbSession) -> list[FolderOut]:
    pairs = await folders_service.list_folders_with_counts(db, workspace.id)
    results: list[FolderOut] = []
    for folder, count in pairs:
        out = FolderOut.model_validate(folder)
        out.document_count = count
        results.append(out)
    return results


@router.post("/workspaces/{workspace_id}/folders", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(workspace: MemberWorkspace, payload: FolderCreate, db: DbSession) -> FolderOut:
    folder = await folders_service.create_folder(db, workspace, payload.name)
    return FolderOut.model_validate(folder)


@router.patch("/folders/{folder_id}", response_model=FolderOut)
async def rename_folder(folder: FolderResource, payload: FolderUpdate, db: DbSession) -> FolderOut:
    renamed = await folders_service.rename_folder(db, folder, payload.name)
    return FolderOut.model_validate(renamed)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(folder: FolderResource, db: DbSession) -> None:
    await folders_service.delete_folder(db, folder)
