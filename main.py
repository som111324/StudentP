from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is not set")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.student_management_system

# Pydantic models
class StudentCreate(BaseModel):
    name: str
    email: str
    age: int
    grade: Optional[str] = None

class Student(StudentCreate):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True  # Use for Pydantic V2.x+

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = None

# Helper function to convert MongoDB ObjectId to string
def student_helper(student) -> dict:
    return {
        "id": str(student["_id"]),
        "name": student["name"],
        "email": student["email"],
        "age": student["age"],
        "grade": student.get("grade"),
    }

# API endpoints
@app.post("/students", response_model=Student, status_code=201)
async def create_student(student: StudentCreate):
    new_student = await db.students.insert_one(student.dict())
    created_student = await db.students.find_one({"_id": new_student.inserted_id})
    return student_helper(created_student)

@app.get("/students", response_model=List[Student])
async def get_students():
    students = []
    async for student in db.students.find():
        students.append(student_helper(student))
    return students

@app.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str):
    try:
        student = await db.students.find_one({"_id": ObjectId(student_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid student ID format")
    if student:
        return student_helper(student)
    raise HTTPException(status_code=404, detail="Student not found")

@app.put("/students/{student_id}", response_model=Student)
async def update_student(student_id: str, student_update: StudentUpdate):
    update_data = {k: v for k, v in student_update.dict().items() if v is not None}
    if len(update_data) < 1:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    try:
        student = await db.students.find_one_and_update(
            {"_id": ObjectId(student_id)},
            {"$set": update_data},
            return_document=True
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid student ID format")
    
    if student:
        return student_helper(student)
    raise HTTPException(status_code=404, detail="Student not found")

@app.delete("/students/{student_id}", status_code=204)
async def delete_student(student_id: str):
    try:
        delete_result = await db.students.delete_one({"_id": ObjectId(student_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid student ID format")
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return None

@app.get("/healthz")
def health_check():
    return {"status": "ok"}


# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
