import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";

import Login from "./login";
import Register from "./register";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;
const WS_URL = import.meta.env.VITE_WS_URL;

/* =========================================================
   DOCUMENT EDITOR
========================================================= */

function DocumentEditor() {
  const navigate = useNavigate();

  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const [connected, setConnected] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);

  const username = localStorage.getItem("username");

  /* =========================================================
     CHECK LOGIN
  ========================================================= */

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      navigate("/login");
    }
  }, [navigate]);

  /* =========================================================
     LOAD DOCUMENTS
  ========================================================= */

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const response = await fetch(`${API_URL}/api/documents`);

        if (!response.ok) {
          throw new Error("Failed to load documents");
        }

        const data = await response.json();

        setDocuments(data);

        if (data.length > 0) {
          setSelectedDoc(data[0]);
          setTitle(data[0].title);
          setContent(data[0].content || "");
        }
      } catch (error) {
        console.error("Error loading documents:", error);
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, []);

  /* =========================================================
     WEBSOCKET REAL-TIME COLLABORATION
  ========================================================= */

  useEffect(() => {
    if (!selectedDoc || isCreating) {
      return;
    }

    const socket = new WebSocket(
      `${WS_URL}/ws/documents/${selectedDoc.id}`
    );

    socket.onopen = () => {
      console.log("WebSocket connected");
      setConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "document_update") {
          setTitle(data.title);
          setContent(data.content);

          setDocuments((previousDocuments) =>
            previousDocuments.map((doc) =>
              doc.id === selectedDoc.id
                ? {
                    ...doc,
                    title: data.title,
                    content: data.content,
                  }
                : doc
            )
          );
        }
      } catch (error) {
        console.error("WebSocket message error:", error);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnected(false);
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setConnected(false);
    };

    return () => {
      socket.close();
      setConnected(false);
    };
  }, [selectedDoc, isCreating]);

  /* =========================================================
     SELECT DOCUMENT
  ========================================================= */

  const selectDocument = (doc) => {
    setIsCreating(false);
    setSelectedDoc(doc);
    setTitle(doc.title);
    setContent(doc.content || "");
  };

  /* =========================================================
     CREATE DOCUMENT
  ========================================================= */

  const createDocument = async () => {
    try {
      const response = await fetch(`${API_URL}/api/documents`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: "Untitled Document",
          content: "",
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to create document");
      }

      const newDocument = await response.json();

      setDocuments((previousDocuments) => [
        ...previousDocuments,
        newDocument,
      ]);

      setSelectedDoc(newDocument);
      setTitle(newDocument.title);
      setContent(newDocument.content || "");
      setIsCreating(false);
    } catch (error) {
      console.error("Create document error:", error);
      alert("Failed to create document");
    }
  };

  /* =========================================================
     UPDATE DOCUMENT
  ========================================================= */

  const updateDocument = async () => {
    if (!selectedDoc) {
      return;
    }

    if (!title.trim()) {
      alert("Title cannot be empty");
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/documents/${selectedDoc.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: title,
            content: content,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update document");
      }

      const updatedDocument = await response.json();

      setDocuments((previousDocuments) =>
        previousDocuments.map((doc) =>
          doc.id === selectedDoc.id
            ? updatedDocument
            : doc
        )
      );

      setSelectedDoc(updatedDocument);

      alert("Document saved successfully");
    } catch (error) {
      console.error("Update document error:", error);
      alert("Failed to save document");
    }
  };

  /* =========================================================
     DELETE DOCUMENT
  ========================================================= */

  const deleteDocument = async () => {
    if (!selectedDoc) {
      return;
    }

    const confirmDelete = window.confirm(
      "Are you sure you want to delete this document?"
    );

    if (!confirmDelete) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/documents/${selectedDoc.id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to delete document");
      }

      const remainingDocuments = documents.filter(
        (doc) => doc.id !== selectedDoc.id
      );

      setDocuments(remainingDocuments);

      if (remainingDocuments.length > 0) {
        setSelectedDoc(remainingDocuments[0]);
        setTitle(remainingDocuments[0].title);
        setContent(remainingDocuments[0].content || "");
      } else {
        setSelectedDoc(null);
        setTitle("");
        setContent("");
      }
    } catch (error) {
      console.error("Delete document error:", error);
      alert("Failed to delete document");
    }
  };

  /* =========================================================
     AUTO SAVE
  ========================================================= */

  useEffect(() => {
    if (!selectedDoc || isCreating) {
      return;
    }

    if (!title.trim()) {
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setAutoSaving(true);

        const response = await fetch(
          `${API_URL}/api/documents/${selectedDoc.id}`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              title: title,
              content: content,
            }),
          }
        );

        if (!response.ok) {
          throw new Error("Auto-save failed");
        }

        setDocuments((previousDocuments) =>
          previousDocuments.map((doc) =>
            doc.id === selectedDoc.id
              ? {
                  ...doc,
                  title: title,
                  content: content,
                }
              : doc
          )
        );

        console.log("Auto-saved successfully");
      } catch (error) {
        console.error("Auto-save error:", error);
      } finally {
        setAutoSaving(false);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [title, content, selectedDoc, isCreating]);

  /* =========================================================
     LOGOUT
  ========================================================= */

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");

    navigate("/login");
  };

  /* =========================================================
     LOADING
  ========================================================= */

  if (loading) {
    return (
      <div className="app-loading">
        Loading...
      </div>
    );
  }

  /* =========================================================
     UI
  ========================================================= */

  return (
    <div className="app-container">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="sidebar-header">
          <h2>CollabDocs</h2>
        </div>

        <button
          className="new-document-button"
          onClick={createDocument}
        >
          + New Document
        </button>

        <div className="document-list">

          {documents.length === 0 ? (
            <p className="no-documents">
              No documents
            </p>
          ) : (
            documents.map((doc) => (
              <button
                key={doc.id}
                className={
                  selectedDoc?.id === doc.id
                    ? "document-item active"
                    : "document-item"
                }
                onClick={() => selectDocument(doc)}
              >
                {doc.title || "Untitled Document"}
              </button>
            ))
          )}

        </div>

      </aside>

      {/* MAIN AREA */}

      <main className="main-content">

        {/* HEADER */}

        <header className="top-bar">

          <div>
            <h1>Document Editor</h1>

            {username && (
              <p className="user-info">
                Logged in as: {username}
              </p>
            )}
          </div>

          <div className="top-bar-actions">

            <span
              className={
                connected
                  ? "connection-status connected"
                  : "connection-status disconnected"
              }
            >
              {connected ? "● Connected" : "● Disconnected"}
            </span>

            {autoSaving && (
              <span className="saving-status">
                Auto-saving...
              </span>
            )}

            <button
              className="logout-button"
              onClick={logout}
            >
              Logout
            </button>

          </div>

        </header>

        {/* EDITOR */}

        {selectedDoc ? (
          <section className="editor-section">

            <input
              className="document-title"
              type="text"
              value={title}
              onChange={(event) =>
                setTitle(event.target.value)
              }
              placeholder="Document title"
            />

            <textarea
              className="document-editor"
              value={content}
              onChange={(event) =>
                setContent(event.target.value)
              }
              placeholder="Start typing your document..."
            />

            <div className="editor-actions">

              <button
                className="save-button"
                onClick={updateDocument}
              >
                Save
              </button>

              <button
                className="delete-button"
                onClick={deleteDocument}
              >
                Delete
              </button>

            </div>

          </section>
        ) : (
          <section className="empty-editor">

            <h2>No document selected</h2>

            <p>
              Create a new document to start collaborating.
            </p>

            <button
              className="new-document-button"
              onClick={createDocument}
            >
              + Create Document
            </button>

          </section>
        )}

      </main>

    </div>
  );
}

/* =========================================================
   APP ROUTING
========================================================= */

function App() {
  return (
    <BrowserRouter>

      <Routes>

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/register"
          element={<Register />}
        />

        <Route
          path="/"
          element={<DocumentEditor />}
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/login"
              replace
            />
          }
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;