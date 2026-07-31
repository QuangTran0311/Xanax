"""API Routes — Knowledge documents ("phòng tư liệu" cho RAG)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub.database import (
    create_knowledge_document, list_knowledge_documents, get_knowledge_document,
    update_knowledge_document, delete_knowledge_document,
)
from core.rag import rag_search

router = APIRouter()


class DocCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field("")
    project_id: int | None = None
    tags: str = Field("")


class DocUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    project_id: int | None = None
    tags: str | None = None


@router.get("")
async def list_docs(project_id: int | None = None):
    docs = await list_knowledge_documents(project_id=project_id)
    return {"documents": docs}


@router.post("", status_code=201)
async def create_doc(body: DocCreate):
    doc_id = await create_knowledge_document(
        title=body.title, content=body.content, project_id=body.project_id, tags=body.tags,
    )
    return await get_knowledge_document(doc_id)


@router.get("/search")
async def search_docs(q: str, project_id: int | None = None, top_k: int = 5):
    results = await rag_search(q, project_id=project_id, top_k=top_k)
    return {"results": results}


@router.get("/{doc_id}")
async def get_doc(doc_id: int):
    doc = await get_knowledge_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.patch("/{doc_id}")
async def update_doc(doc_id: int, body: DocUpdate):
    doc = await get_knowledge_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    kwargs = {k: getattr(body, k) for k in body.model_fields_set}
    if kwargs:
        await update_knowledge_document(doc_id, **kwargs)
    return await get_knowledge_document(doc_id)


@router.delete("/{doc_id}", status_code=204)
async def remove_doc(doc_id: int):
    if not await delete_knowledge_document(doc_id):
        raise HTTPException(404, "Document not found")
