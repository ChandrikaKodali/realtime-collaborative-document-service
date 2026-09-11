from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Document, User
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
)

# =========================================================
# CREATE APP
# =========================================================

app = FastAPI(
    title="Real-Time Collaborative Document Service",
    version="1.0.0",
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

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class DocumentCreate(BaseModel):
    title: str
    content: str = ""


class DocumentUpdate(BaseModel):
    title: str
    content: str


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Real-Time Collaborative Document Service is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# AUTHENTICATION
# =========================================================

@app.post("/api/auth/register")
def register_user(user_data: RegisterRequest):

    db: Session = SessionLocal()

    try:

        # Check username
        existing_username = (
            db.query(User)
            .filter(User.username == user_data.username)
            .first()
        )

        if existing_username:
            return {
                "error": "Username already exists"
            }

        # Check email
        existing_email = (
            db.query(User)
            .filter(User.email == user_data.email)
            .first()
        )

        if existing_email:
            return {
                "error": "Email already exists"
            }

        # Create user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
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

    except Exception as e:

        db.rollback()

        print("REGISTER ERROR:", e)

        raise e

    finally:

        db.close()


@app.post("/api/auth/login")
def login_user(user_data: LoginRequest):

    db: Session = SessionLocal()

    try:

        # Find user
        user = (
            db.query(User)
            .filter(User.username == user_data.username)
            .first()
        )

        # User not found
        if not user:

            return {
                "error": "Invalid username or password"
            }

        # Check password
        if not verify_password(
            user_data.password,
            user.password_hash,
        ):

            return {
                "error": "Invalid username or password"
            }

        # Create JWT token
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "username": user.username,
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
        }

    except Exception as e:

        print("LOGIN ERROR:", e)

        raise e

    finally:

        db.close()


# =========================================================
# DOCUMENT APIs
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

            return {
                "error": "Document not found"
            }

        return document

    finally:

        db.close()


@app.post("/api/documents")
def create_document(
    document_data: DocumentCreate
):

    db: Session = SessionLocal()

    try:

        new_document = Document(
            title=document_data.title,
            content=document_data.content,
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        return new_document

    except Exception as e:

        db.rollback()

        print("CREATE DOCUMENT ERROR:", e)

        raise e

    finally:

        db.close()


@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
):

    db: Session = SessionLocal()

    try:

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
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

        print("UPDATE DOCUMENT ERROR:", e)

        raise e

    finally:

        db.close()


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int):

    db = SessionLocal()

    try:

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:

            return {
                "error": "Document not found"
            }

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

            if (
                websocket
                in self.active_connections[document_id]
            ):

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
# WEBSOCKET
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

    except Exception as e:

        print("WEBSOCKET ERROR:", e)

        manager.disconnect(
            websocket,
            document_id,
        )