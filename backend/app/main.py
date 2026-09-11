from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Document


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Real-Time Collaborative Document Service",
    version="1.0.0"
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://collabdocs-frontend-i4q4.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class DocumentCreate(BaseModel):
    title: str
    content: str = ""


class DocumentUpdate(BaseModel):
    title: str
    content: str


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "message": "Real-Time Collaborative Document Service is running"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# =========================================================
# GET ALL DOCUMENTS
# =========================================================

@app.get("/api/documents")
def get_documents():

    db: Session = SessionLocal()

    try:

        documents = (
            db.query(Document)
            .order_by(Document.id.desc())
            .all()
        )

        return documents

    finally:

        db.close()


# =========================================================
# GET ONE DOCUMENT
# =========================================================

@app.get("/api/documents/{document_id}")
def get_document(document_id: int):

    db: Session = SessionLocal()

    try:

        document = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        if not document:

            return {
                "error": "Document not found"
            }

        return document

    finally:

        db.close()


# =========================================================
# CREATE DOCUMENT
# =========================================================

@app.post("/api/documents")
def create_document(
    document_data: DocumentCreate
):

    db: Session = SessionLocal()

    try:

        new_document = Document(
            title=document_data.title,
            content=document_data.content
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        return new_document

    except Exception as e:

        db.rollback()

        print(
            "CREATE DOCUMENT ERROR:",
            e
        )

        raise e

    finally:

        db.close()


# =========================================================
# UPDATE DOCUMENT
# =========================================================

@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    document_data: DocumentUpdate
):

    db: Session = SessionLocal()

    try:

        document = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        if not document:

            return {
                "error": "Document not found"
            }

        document.title = document_data.title
        document.content = document_data.content

        db.commit()
        db.refresh(document)

        return document

    except Exception as e:

        db.rollback()

        print(
            "UPDATE DOCUMENT ERROR:",
            e
        )

        raise e

    finally:

        db.close()


# =========================================================
# DELETE DOCUMENT
# =========================================================

@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: int
):

    db: Session = SessionLocal()

    try:

        document = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        if not document:

            return {
                "error": "Document not found"
            }

        db.delete(document)
        db.commit()

        return {
            "message":
                "Document deleted successfully"
        }

    except Exception as e:

        db.rollback()

        print(
            "DELETE DOCUMENT ERROR:",
            e
        )

        raise e

    finally:

        db.close()


# =========================================================
# WEBSOCKET MANAGER
# =========================================================

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

            self.active_connections[
                document_id
            ] = []

        self.active_connections[
            document_id
        ].append(websocket)


    def disconnect(
        self,
        websocket: WebSocket,
        document_id: int
    ):

        if document_id in self.active_connections:

            if websocket in self.active_connections[
                document_id
            ]:

                self.active_connections[
                    document_id
                ].remove(websocket)

            if not self.active_connections[
                document_id
            ]:

                del self.active_connections[
                    document_id
                ]


    async def broadcast(
        self,
        message: str,
        document_id: int,
        sender: WebSocket
    ):

        if document_id not in self.active_connections:

            return

        for connection in self.active_connections[
            document_id
        ]:

            if connection != sender:

                try:

                    await connection.send_text(
                        message
                    )

                except Exception:

                    pass


manager = ConnectionManager()


# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket(
    "/ws/documents/{document_id}"
)
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

        print(
            "WEBSOCKET ERROR:",
            e
        )

        manager.disconnect(
            websocket,
            document_id
        )