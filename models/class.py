from pydantic import BaseModel
from typing import List, Optional


class ClassBase(BaseModel):
    title: str
    teacher_name: str
    schedule: Optional[str] = None
    students: List[int] = []  # List of student IDs


class ClassCreate(ClassBase):
    pass


class ClassResponse(ClassBase):
    id: int


class Class(ClassBase):
    id: int