from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from .models import User, Document
from .schemas import DocumentCreate, DocumentUpdate, RegisterRequest, LoginRequest
from .auth import hash_password, verify_password, create_access_token, verify_token


# =========================================================
# CREATE FASTAPI APP
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
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Real-Time Collaborative Document Service is running"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected"
    }


# =========================================================
# AUTHENTICATION
# =========================================================

@app.post("/api/auth/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_username = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    existing_email = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

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
# LOGIN
# =========================================================

@app.post("/api/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(
            (User.username == request.username)
            | (User.email == request.username)
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "user_id": user.id,
    }


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    token: str,
    db: Session
):
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


# =========================================================
# DOCUMENTS - GET ALL
# =========================================================

@app.get("/api/documents")
def get_documents(
    db: Session = Depends(get_db)
):
    documents = (
        db.query(Document)
        .order_by(Document.id.desc())
        .all()
    )

    return documents


# =========================================================
# DOCUMENT - GET ONE
# =========================================================

@app.get("/api/documents/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return document


# =========================================================
# DOCUMENT - CREATE
# =========================================================

@app.post("/api/documents")
def create_document(
    request: DocumentCreate,
    db: Session = Depends(get_db)
):
    document = Document(
        title=request.title,
        content=request.content,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


# =========================================================
# DOCUMENT - UPDATE
# =========================================================

@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    request: DocumentUpdate,
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    if request.title is not None:
        document.title = request.title

    if request.content is not None:
        document.content = request.content

    db.commit()
    db.refresh(document)

    return document


# =========================================================
# DOCUMENT - DELETE
# =========================================================

@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
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
        self.active_connections: dict[
            int,
            list[WebSocket]
        ] = {}

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


# =========================================================
# WEBSOCKET - REAL-TIME COLLABORATION
# =========================================================

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

    except Exception:

        manager.disconnect(
            websocket,
            document_id
        )