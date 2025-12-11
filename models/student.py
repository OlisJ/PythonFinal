from pydantic import BaseModel
from typing import List, Optional



class StudentBase(BaseModel):
    name: str
    email: str
    age: Optional[int] = None
    enrolled_classes: List[int] = []   



class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    id: int



class Student(StudentBase):
    id: int
