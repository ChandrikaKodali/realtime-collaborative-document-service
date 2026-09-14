@app.post("/api/auth/login") # type: ignore
def login(request: LoginRequest, db: Session = Depends(get_db)): # type: ignore
    user = (
        db.query(User) # type: ignore
        .filter(
            (User.username == request.username) # type: ignore
            | (User.email == request.username) # type: ignore
        )
        .first()
    )

    if user is None:
        raise HTTPException( # type: ignore
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(request.password, user.password_hash): # type: ignore
        raise HTTPException( # type: ignore
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token({ # type: ignore
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