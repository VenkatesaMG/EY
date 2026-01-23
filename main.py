import shutil
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

origins = ["*"]
UPLOAD_DIR = "provider_documents"

# 3. Add the Middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/create_profile")
async def create_profile(
    payload: str = Form(...),
    attachment: List[UploadFile] = File(...)
):
    for file in attachment:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)

    return {"status": "saved", "file": attachment.filename}