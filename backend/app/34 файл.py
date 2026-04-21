# Добавьте эти импорты в начало файла
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets

# Модели для пользователей
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    username: str
    email: str

# Временное хранилище пользователей
users_db = []
current_user_id = 1

# Эндпоинты для регистрации
@app.post("/api/v1/auth/register")
def register(user: UserCreate):
    global current_user_id
    # Проверка существования
    for u in users_db:
        if u.email == user.email:
            return {"error": "Email already exists"}
    
    # Создание пользователя
    new_user = User(
        id=current_user_id,
        username=user.username,
        email=user.email
    )
    users_db.append(new_user)
    current_user_id += 1
    
    return {"message": "User created", "user": new_user}

@app.post("/api/v1/auth/login")
def login(user: UserLogin):
    for u in users_db:
        if u.email == user.email:
            return {"message": "Login successful", "user": u}
    return {"error": "Invalid credentials"}