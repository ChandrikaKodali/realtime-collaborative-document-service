from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User, Document
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
)


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Real-Time Collaborative Document Service",
    description="A real-time collaborative document editing service",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# SECURITY
# =========================================================

security = HTTPBearer(auto_error=False)


# =========================================================
# REQUEST MODELS
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DocumentCreate(BaseModel):
    title: str
    content: str = ""


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


# =========================================================
# HELPER - GET CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


# =========================================================
# ROOT / HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Real-Time Collaborative Document Service is running",
        "status": "healthy",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
    }


# =========================================================
# AUTHENTICATION - REGISTER
# =========================================================

@app.post("/api/auth/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    # Check username
    existing_username = db.query(User).filter(
        User.username == request.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists",
        )

    # Check email
    existing_email = db.query(User).filter(
        User.email == request.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    # Create user
    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Registration successful",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
        },
    }


# =========================================================
# AUTHENTICATION - LOGIN
# =========================================================

@app.post("/api/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "user_id": user.id,
    }


# =========================================================
# GET ALL DOCUMENTS
# =========================================================

@app.get("/api/documents")
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documents = (
        db.query(Document)
        .filter(
            (Document.owner_id == current_user.id)
            | (Document.owner_id.is_(None))
        )
        .order_by(Document.updated_at.desc())
        .all()
    )

    return [
        {
            "id": document.id,
            "title": document.title,
            "content": document.content or "",
            "owner_id": document.owner_id,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        }
        for document in documents
    ]


# =========================================================
# GET SINGLE DOCUMENT
# =========================================================

@app.get("/api/documents/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        document.owner_id is not None
        and document.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this document",
        )

    return {
        "id": document.id,
        "title": document.title,
        "content": document.content or "",
        "owner_id": document.owner_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


# =========================================================
# CREATE DOCUMENT
# =========================================================

@app.post("/api/documents")
def create_document(
    request: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = Document(
        title=request.title,
        content=request.content,
        owner_id=current_user.id,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "title": document.title,
        "content": document.content or "",
        "owner_id": document.owner_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


# =========================================================
# UPDATE DOCUMENT
# =========================================================

@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    request: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        document.owner_id is not None
        and document.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to edit this document",
        )

    if request.title is not None:
        document.title = request.title

    if request.content is not None:
        document.content = request.content

    document.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "title": document.title,
        "content": document.content or "",
        "owner_id": document.owner_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


# =========================================================
# DELETE DOCUMENT
# =========================================================

@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if (
        document.owner_id is not None
        and document.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this document",
        )

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully"
    }


# =========================================================
# WEBSOCKET CONNECTION MANAGER
# =========================================================

class ConnectionManager:

    def __init__(self):
        self.active_connections = {}

    async def connect(
        self,
        websocket: WebSocket,
        document_id: int,
    ):
        await websocket.accept()

        if document_id not in self.active_connections:
            self.active_connections[document_id] = []

        self.active_connections[document_id].append(
            websocket
        )

    def disconnect(
        self,
        websocket: WebSocket,
        document_id: int,
    ):
        if document_id in self.active_connections:

            if websocket in self.active_connections[document_id]:
                self.active_connections[document_id].remove(
                    websocket
                )

            if not self.active_connections[document_id]:
                del self.active_connections[
                    document_id
                ]

    async def broadcast(
        self,
        message: str,
        document_id: int,
        sender: WebSocket,
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
# WEBSOCKET - REAL-TIME COLLABORATION
# =========================================================

@app.websocket("/ws/documents/{document_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    document_id: int,
):
    await manager.connect(
        websocket,
        document_id,
    )

    try:

        while True:

            message = await websocket.receive_text()

            await manager.broadcast(
                message,
                document_id,
                websocket,
            )

    except WebSocketDisconnect:

        manager.disconnect(
            websocket,
            document_id,
        )

    except Exception:

        manager.disconnect(
            websocket,
            document_id,
        )