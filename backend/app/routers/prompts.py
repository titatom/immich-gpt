import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.prompt_template import PromptTemplate
from ..schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateOut

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=List[PromptTemplateOut])
def list_prompts(
    prompt_type: Optional[str] = None,
    bucket_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(PromptTemplate)
    if prompt_type:
        q = q.filter(PromptTemplate.prompt_type == prompt_type)
    if bucket_id:
        q = q.filter(PromptTemplate.bucket_id == bucket_id)
    return q.order_by(PromptTemplate.prompt_type, PromptTemplate.version.desc()).all()


@router.post("", response_model=PromptTemplateOut)
def create_prompt(body: PromptTemplateCreate, db: Session = Depends(get_db)):
    pt = PromptTemplate(
        id=str(uuid.uuid4()),
        prompt_type=body.prompt_type,
        name=body.name,
        content=body.content,
        enabled=body.enabled,
        version=1,
        bucket_id=body.bucket_id,
    )
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return pt


@router.get("/{prompt_id}", response_model=PromptTemplateOut)
def get_prompt(prompt_id: str, db: Session = Depends(get_db)):
    pt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return pt


@router.patch("/{prompt_id}", response_model=PromptTemplateOut)
def update_prompt(prompt_id: str, body: PromptTemplateUpdate, db: Session = Depends(get_db)):
    pt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if body.name is not None:
        pt.name = body.name
    if body.content is not None:
        pt.content = body.content
        pt.version = (pt.version or 1) + 1
    if body.enabled is not None:
        pt.enabled = body.enabled
    db.commit()
    db.refresh(pt)
    return pt


@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str, db: Session = Depends(get_db)):
    pt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(pt)
    db.commit()
    return {"deleted": True}
