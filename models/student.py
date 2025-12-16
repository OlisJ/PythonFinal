from pydantic import BaseModel
from typing import Optional



class StudentBase(BaseModel):
    name: str
    email: str
    age: Optional[int] = None   



class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    id: int



class Student(StudentBase):
    id: int
    id: int
