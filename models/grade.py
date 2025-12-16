from pydantic import BaseModel
from typing import Optional

class GradeBase(BaseModel):
    student_id: int
    score: float


class GradeCreate(GradeBase):
    pass


class GradeResponse(GradeBase):
    id: int


class Grade(GradeBase):
    id: int