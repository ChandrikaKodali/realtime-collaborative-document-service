from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Document

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Pydantic Models
# -----------------------------

class DocumentCreate(BaseModel):
    title: str
    content: str = ""


class DocumentUpdate(BaseModel):
    title: str
    content: str = ""


# -----------------------------
# Basic Routes
# -----------------------------

@app.get("/")
def root():
    return {
        "message": "Real-Time Collaborative Document Service"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# -----------------------------
# Get All Documents
# -----------------------------

@app.get("/api/documents")
def get_documents():
    db: Session = SessionLocal()

    try:
        documents = (
            db.query(Document)
            .order_by(Document.id)
            .all()
        )

        return [
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content or ""
            }
            for doc in documents
        ]

    finally:
        db.close()


# -----------------------------
# Get One Document
# -----------------------------

@app.get("/api/documents/{document_id}")
def get_document(document_id: int):
    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            return {"error": "Document not found"}

        return {
            "id": document.id,
            "title": document.title,
            "content": document.content or ""
        }

    finally:
        db.close()


# -----------------------------
# Create Document
# -----------------------------

@app.post("/api/documents")
def create_document(document_data: DocumentCreate):
    db: Session = SessionLocal()

    try:
        new_document = Document(
            title=document_data.title,
            content=document_data.content
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        return {
            "message": "Document created successfully",
            "document": {
                "id": new_document.id,
                "title": new_document.title,
                "content": new_document.content or ""
            }
        }

    except Exception as e:
        db.rollback()
        print("CREATE DOCUMENT ERROR:", e)
        raise e

    finally:
        db.close()


# -----------------------------
# Update Document
# -----------------------------

@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    document_data: DocumentUpdate
):
    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            return {"error": "Document not found"}

        document.title = document_data.title
        document.content = document_data.content

        db.commit()
        db.refresh(document)

        return {
            "message": "Document updated successfully",
            "document": {
                "id": document.id,
                "title": document.title,
                "content": document.content or ""
            }
        }

    except Exception as e:
        db.rollback()
        print("UPDATE DOCUMENT ERROR:", e)
        raise e

    finally:
        db.close()


# -----------------------------
# Delete Document
# -----------------------------

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int):
    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            return {"error": "Document not found"}

        db.delete(document)
        db.commit()

        return {
            "message": "Document deleted successfully"
        }

    except Exception as e:
        db.rollback()
        print("DELETE DOCUMENT ERROR:", e)
        raise e

    finally:
        db.close()


# -----------------------------
# WebSocket Manager
# -----------------------------

class ConnectionManager:

    def __init__(self):
        self.active_connections = {}

    async def connect(
        self,
        websocket: WebSocket,
        document_id: int
    ):
        await websocket.accept()

        if document_id not in self.active_connections:
            self.active_connections[document_id] = []

        self.active_connections[document_id].append(
            websocket
        )

        print(
            f"WebSocket connected for document {document_id}"
        )

    def disconnect(
        self,
        websocket: WebSocket,
        document_id: int
    ):
        if document_id in self.active_connections:

            if websocket in self.active_connections[document_id]:
                self.active_connections[document_id].remove(
                    websocket
                )

            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

        print(
            f"WebSocket disconnected for document {document_id}"
        )

    async def broadcast(
        self,
        message: str,
        document_id: int,
        sender: WebSocket
    ):
        if document_id not in self.active_connections:
            return

        for connection in self.active_connections[document_id]:

            if connection != sender:

                try:
                    await connection.send_text(message)
                except Exception:
                    pass


manager = ConnectionManager()


# -----------------------------
# WebSocket Endpoint
# -----------------------------

@app.websocket("/ws/documents/{document_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    document_id: int
):
    await manager.connect(
        websocket,
        document_id
    )

    try:

        while True:

            message = await websocket.receive_text()

            await manager.broadcast(
                message,
                document_id,
                websocket
            )

    except WebSocketDisconnect:

        manager.disconnect(
            websocket,
            document_id
        )

    except Exception as e:

        print("WEBSOCKET ERROR:", e)

        manager.disconnect(
            websocket,
            document_id
        )