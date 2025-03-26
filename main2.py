from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import sqlite3
import uvicorn
import os
import json
import shutil

# Configuration (adjust as needed)
DATABASE_FILE = "database.db"  # Path to your unified database
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = FastAPI(title="Legal Evidence Processing API")

# Dependency: get a database connection
def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        yield conn
    finally:
        conn.close()

# Endpoint: Upload a video file (.mov)
@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename.endswith(".mov"):
        raise HTTPException(status_code=400, detail="Only .mov files are accepted for now.")
    
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())
    
    # TODO: Process the video file:
    # - Convert .mov to MP4 if needed using FFmpeg.
    # - Run OpenAI Whisper transcription.
    # - Check transcription confidence (flag if below 75%).
    # - Save results in the database with a unique chronological ID.
    
    return JSONResponse(content={"info": f"Video '{file.filename}' uploaded and queued for processing.", "file_location": file_location})

# Endpoint: Upload a document (for OCR via Tesseract)
@app.post("/upload/document")
async def upload_document(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())
    
    # TODO: Process the document:
    # - Run Tesseract OCR.
    # - Extract metadata (Author, Date, Recipient, etc.), even if some info is missing.
    # - Save OCR text and metadata in the database.
    
    return JSONResponse(content={"info": f"Document '{file.filename}' uploaded and queued for OCR processing.", "file_location": file_location})

# Endpoint: Retrieve transcriptions; optionally only flagged ones
@app.get("/transcriptions")
def get_transcriptions(flagged: bool = False, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    if flagged:
        # Assuming a 'confidence' field exists in your transcriptions table
        cursor.execute("SELECT * FROM transcriptions WHERE confidence < 75")
    else:
        cursor.execute("SELECT * FROM transcriptions")
    rows = cursor.fetchall()
    # Convert rows to a list of dicts if needed
    return {"transcriptions": rows}

# Endpoint: Generate report (CSV or PDF export)
@app.get("/reports")
def generate_report(report_type: str = "csv", db: sqlite3.Connection = Depends(get_db)):
    # TODO: Generate report from processed data
    # This could include metadata fields such as Author, Date, Recipient, Subject, Unique ID, etc.
    # and apply your combined keyword/vector search filters.
    return {"info": f"Report generated as {report_type}. (Functionality to be implemented)"}

# Endpoint: Search using keywords and/or vector-based semantic search
@app.get("/search")
def search_files(query: str, db: sqlite3.Connection = Depends(get_db)):
    # TODO: Implement search functionality:
    # - Traditional keyword search on metadata.
    # - Vector-based semantic search using cached OpenAI embeddings.
    return {"info": f"Search results for query: '{query}' (Functionality to be implemented)"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)