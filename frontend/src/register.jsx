import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const API_URL = import.meta.env.VITE_API_URL;

function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (event) => {
    event.preventDefault();

    if (!username.trim() || !email.trim() || !password.trim()) {
      alert("Please fill all fields.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      alert("Registration successful!");

      navigate("/login");
    } catch (error) {
      console.error("Registration error:", error);
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#f4f0ff",
        padding: "20px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          background: "#ffffff",
          padding: "40px",
          borderRadius: "16px",
          boxSizing: "border-box",
          boxShadow: "0 12px 30px rgba(60, 40, 90, 0.12)",
        }}
      >
        <h1
          style={{
            margin: "0 0 10px 0",
            textAlign: "center",
            color: "#2d2142",
            fontSize: "40px",
            fontWeight: "700",
          }}
        >
          Create Account
        </h1>

        <p
          style={{
            margin: "0 0 30px 0",
            textAlign: "center",
            color: "#777",
            fontSize: "15px",
          }}
        >
          Create your CollabDocs account
        </p>

        <form
          onSubmit={handleRegister}
          style={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <label
            style={{
              marginBottom: "8px",
              color: "#3d3152",
              fontSize: "15px",
              fontWeight: "600",
            }}
          >
            Username
          </label>

          <input
            type="text"
            placeholder="Enter username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            style={{
              width: "100%",
              height: "44px",
              padding: "0 12px",
              marginBottom: "20px",
              boxSizing: "border-box",
              border: "1px solid #d5cce5",
              borderRadius: "8px",
              fontSize: "14px",
            }}
          />

          <label
            style={{
              marginBottom: "8px",
              color: "#3d3152",
              fontSize: "15px",
              fontWeight: "600",
            }}
          >
            Email
          </label>

          <input
            type="email"
            placeholder="Enter email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            style={{
              width: "100%",
              height: "44px",
              padding: "0 12px",
              marginBottom: "20px",
              boxSizing: "border-box",
              border: "1px solid #d5cce5",
              borderRadius: "8px",
              fontSize: "14px",
            }}
          />

          <label
            style={{
              marginBottom: "8px",
              color: "#3d3152",
              fontSize: "15px",
              fontWeight: "600",
            }}
          >
            Password
          </label>

          <input
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            style={{
              width: "100%",
              height: "44px",
              padding: "0 12px",
              marginBottom: "20px",
              boxSizing: "border-box",
              border: "1px solid #d5cce5",
              borderRadius: "8px",
              fontSize: "14px",
            }}
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              height: "44px",
              border: "none",
              borderRadius: "8px",
              background: "#76509a",
              color: "#ffffff",
              fontSize: "15px",
              fontWeight: "600",
              cursor: "pointer",
            }}
          >
            {loading ? "Creating Account..." : "Register"}
          </button>
        </form>

        <p
          style={{
            margin: "24px 0 0 0",
            textAlign: "center",
            color: "#666",
            fontSize: "15px",
          }}
        >
          Already have an account?{" "}
          <Link
            to="/login"
            style={{
              color: "#6f4c8b",
              fontWeight: "600",
              textDecoration: "none",
            }}
          >
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default Register;