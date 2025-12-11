from pydantic import BaseModel
from typing import List, Optional

class GradeBase(BaseModel):
    student_id: int
    class_id: int
    score: float
    feedback: Optional[str] = None


class GradeCreate(GradeBase):
    pass


class GradeResponse(GradeBase):
    id: int


class Grade(GradeBase):
    id: int