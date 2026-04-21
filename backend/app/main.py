from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os

SECRET_KEY = "your-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

UPLOAD_DIR = "uploads"
QUICK_DIR = "uploads/quick"
COVERS_DIR = "uploads/covers"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QUICK_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)

app = FastAPI(title="Let's FioHub API")

app.mount("/covers", StaticFiles(directory=COVERS_DIR), name="covers")

# Правильные CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[int]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except:
        return None

# --- МОДЕЛИ ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CommentCreate(BaseModel):
    text: str

class SettingsUpdate(BaseModel):
    theme: str = "dark"
    language: str = "professional"
    video_quality: str = "auto"
    subtitles: bool = False
    font_style: str = "professional"

# --- ХРАНИЛИЩА (в памяти) ---
users_db = []
videos_db = []
quick_videos_db = []
comments_db = []
likes_db = []
dislikes_db = []
subscriptions_db = []
watch_history_db = []
notifications_db = []
user_counter = 1
comment_counter = 1
notification_counter = 1

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_user_by_email(email: str):
    for u in users_db:
        if u["email"] == email:
            return u
    return None

def get_user_by_username(username: str):
    for u in users_db:
        if u["username"] == username:
            return u
    return None

def get_user_by_id(user_id: int):
    for u in users_db:
        if u["id"] == user_id:
            return u
    return None

def has_liked(user_id: int, video_id: str):
    for like in likes_db:
        if like["user_id"] == user_id and like["video_id"] == video_id:
            return True
    return False

def has_disliked(user_id: int, video_id: str):
    for dislike in dislikes_db:
        if dislike["user_id"] == user_id and dislike["video_id"] == video_id:
            return True
    return False

def is_subscribed(subscriber_id: int, channel_id: int):
    for sub in subscriptions_db:
        if sub["subscriber_id"] == subscriber_id and sub["channel_id"] == channel_id:
            return True
    return False

def add_notification(user_id: int, message: str, video_id: str = None):
    global notification_counter
    notifications_db.append({
        "id": notification_counter,
        "user_id": user_id,
        "message": message,
        "video_id": video_id,
        "read": False,
        "created_at": datetime.now().isoformat()
    })
    notification_counter += 1

# --- ПОЛЬЗОВАТЕЛИ ---
@app.get("/")
def root():
    return {"message": "Let's FioHub API"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/register")
def register(user: UserRegister):
    if get_user_by_email(user.email):
        raise HTTPException(400, "Email already exists")
    if get_user_by_username(user.username):
        raise HTTPException(400, "Username already exists")
    
    global user_counter
    new_user = {
        "id": user_counter,
        "username": user.username,
        "email": user.email,
        "password": user.password,
        "channel_name": f"{user.username}'s Channel",
        "channel_description": "",
        "channel_cover": None,
        "subscribers_count": 0,
        "settings": {
            "theme": "dark",
            "language": "professional",
            "video_quality": "auto",
            "subtitles": False,
            "font_style": "professional"
        }
    }
    users_db.append(new_user)
    user_counter += 1
    
    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user["email"],
        "channel_name": new_user["channel_name"]
    }

@app.post("/api/login")
def login(user: UserLogin):
    db_user = get_user_by_email(user.email)
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(401, "Invalid email or password")
    
    token = create_token(db_user["id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "channel_name": db_user["channel_name"],
            "channel_description": db_user.get("channel_description", ""),
            "channel_cover": db_user.get("channel_cover"),
            "settings": db_user.get("settings", {})
        }
    }

@app.get("/api/me")
def get_me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "channel_name": user["channel_name"],
        "channel_description": user.get("channel_description", ""),
        "channel_cover": user.get("channel_cover"),
        "subscribers_count": user.get("subscribers_count", 0),
        "settings": user.get("settings", {})
    }

@app.put("/api/channel")
async def update_channel(
    description: str = Form(""),
    cover: Optional[UploadFile] = File(None),
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    
    for user in users_db:
        if user["id"] == user_id:
            user["channel_description"] = description
            if cover:
                cover_id = str(uuid.uuid4())[:8]
                cover_path = os.path.join(COVERS_DIR, f"{cover_id}.jpg")
                content = await cover.read()
                with open(cover_path, "wb") as f:
                    f.write(content)
                user["channel_cover"] = f"/covers/{cover_id}.jpg"
            return {
                "message": "Channel updated",
                "channel_description": user["channel_description"],
                "channel_cover": user.get("channel_cover")
            }
    raise HTTPException(404, "User not found")

@app.put("/api/settings")
def update_settings(settings: SettingsUpdate, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    for user in users_db:
        if user["id"] == user_id:
            user["settings"] = settings.dict()
            return {"message": "Settings updated", "settings": user["settings"]}
    raise HTTPException(404, "User not found")

@app.get("/api/settings")
def get_settings(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user.get("settings", {"theme": "dark", "language": "professional", "video_quality": "auto", "subtitles": False, "font_style": "professional"})

# --- ПОДПИСКИ ---
@app.post("/api/subscribe/{channel_id}")
def subscribe_channel(channel_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    if user_id == channel_id:
        raise HTTPException(400, "Cannot subscribe to yourself")
    
    channel = get_user_by_id(channel_id)
    if not channel:
        raise HTTPException(404, "Channel not found")
    
    if is_subscribed(user_id, channel_id):
        raise HTTPException(400, "Already subscribed")
    
    subscriptions_db.append({
        "subscriber_id": user_id,
        "channel_id": channel_id,
        "created_at": datetime.now().isoformat()
    })
    channel["subscribers_count"] = channel.get("subscribers_count", 0) + 1
    return {"message": "Subscribed", "subscribers_count": channel["subscribers_count"]}

@app.delete("/api/subscribe/{channel_id}")
def unsubscribe_channel(channel_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    global subscriptions_db
    subscriptions_db = [s for s in subscriptions_db if not (s["subscriber_id"] == user_id and s["channel_id"] == channel_id)]
    channel = get_user_by_id(channel_id)
    if channel:
        channel["subscribers_count"] = max(0, channel.get("subscribers_count", 0) - 1)
    return {"message": "Unsubscribed", "subscribers_count": channel["subscribers_count"] if channel else 0}

@app.get("/api/subscribers/{channel_id}")
def get_subscribers_count(channel_id: int):
    count = sum(1 for s in subscriptions_db if s["channel_id"] == channel_id)
    return {"count": count}

@app.get("/api/subscribers/list/{channel_id}")
def get_subscribers_list(channel_id: int, authorization: Optional[str] = Header(None)):
    subscribers = []
    for sub in subscriptions_db:
        if sub["channel_id"] == channel_id:
            user = get_user_by_id(sub["subscriber_id"])
            if user:
                subscribers.append({"id": user["id"], "username": user["username"]})
    return {"subscribers": subscribers}

@app.get("/api/subscriptions")
def get_my_subscriptions(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    subscriptions = []
    for sub in subscriptions_db:
        if sub["subscriber_id"] == user_id:
            channel = get_user_by_id(sub["channel_id"])
            if channel:
                subscriptions.append({"id": channel["id"], "username": channel["username"], "channel_name": channel["channel_name"]})
    return {"subscriptions": subscriptions}

@app.get("/api/is_subscribed/{channel_id}")
def check_subscribed(channel_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        return {"subscribed": False}
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        return {"subscribed": False}
    return {"subscribed": is_subscribed(user_id, channel_id)}

# --- ВИДЕО ---
@app.get("/api/videos")
def get_all_videos(limit: int = 20, offset: int = 0):
    sorted_videos = sorted(videos_db, key=lambda x: x["created_at"], reverse=True)
    return {"videos": sorted_videos[offset:offset+limit], "total": len(videos_db)}

@app.get("/api/quick")
def get_quick_videos(limit: int = 20, offset: int = 0):
    sorted_videos = sorted(quick_videos_db, key=lambda x: x["created_at"], reverse=True)
    return {"videos": sorted_videos[offset:offset+limit], "total": len(quick_videos_db)}

@app.post("/api/videos/upload")
async def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    is_quick: bool = Form(False),
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    video_id = str(uuid.uuid4())[:8]
    upload_dir = QUICK_DIR if is_quick else UPLOAD_DIR
    file_path = f"{upload_dir}/{video_id}.mp4"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    new_video = {
        "id": video_id, "title": title, "description": description,
        "views": 0, "likes": 0, "dislikes": 0,
        "uploader_id": user["id"], "uploader_name": user["username"],
        "created_at": datetime.now().isoformat(), "file_path": file_path, "is_quick": is_quick
    }
    if is_quick:
        quick_videos_db.append(new_video)
    else:
        videos_db.append(new_video)
    
    for sub in subscriptions_db:
        if sub["channel_id"] == user_id:
            add_notification(sub["subscriber_id"], f"Новое видео от {user['username']}: {title}", video_id)
    return {"message": "Uploaded", "video_id": video_id, "file_size": len(content), "is_quick": is_quick}

@app.get("/api/videos/{video_id}")
def get_video(video_id: str, authorization: Optional[str] = Header(None)):
    for v in videos_db:
        if v["id"] == video_id:
            v["views"] += 1
            if authorization and authorization.startswith("Bearer "):
                token = authorization.replace("Bearer ", "")
                user_id = decode_token(token)
                if user_id:
                    watch_history_db.append({
                        "user_id": user_id,
                        "video_id": video_id,
                        "video_title": v["title"],
                        "watched_at": datetime.now().isoformat()
                    })
            return v
    for v in quick_videos_db:
        if v["id"] == video_id:
            v["views"] += 1
            if authorization and authorization.startswith("Bearer "):
                token = authorization.replace("Bearer ", "")
                user_id = decode_token(token)
                if user_id:
                    watch_history_db.append({
                        "user_id": user_id,
                        "video_id": video_id,
                        "video_title": v["title"],
                        "watched_at": datetime.now().isoformat()
                    })
            return v
    raise HTTPException(404, "Video not found")

@app.get("/api/videos/{video_id}/stream")
def stream_video(video_id: str):
    for v in videos_db:
        if v["id"] == video_id:
            file_path = v.get("file_path", f"{UPLOAD_DIR}/{video_id}.mp4")
            if os.path.exists(file_path):
                return FileResponse(file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})
    for v in quick_videos_db:
        if v["id"] == video_id:
            file_path = v.get("file_path", f"{QUICK_DIR}/{video_id}.mp4")
            if os.path.exists(file_path):
                return FileResponse(file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})
    raise HTTPException(404, "File not found")

@app.post("/api/videos/{video_id}/like")
def like_video(video_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    if has_liked(user_id, video_id):
        raise HTTPException(400, "You already liked this video")
    if has_disliked(user_id, video_id):
        for i, d in enumerate(dislikes_db):
            if d["user_id"] == user_id and d["video_id"] == video_id:
                dislikes_db.pop(i)
                for v in videos_db:
                    if v["id"] == video_id:
                        v["dislikes"] = max(0, v["dislikes"] - 1)
                        break
                for v in quick_videos_db:
                    if v["id"] == video_id:
                        v["dislikes"] = max(0, v["dislikes"] - 1)
                        break
                break
    for v in videos_db:
        if v["id"] == video_id:
            v["likes"] += 1
            likes_db.append({"user_id": user_id, "video_id": video_id, "created_at": datetime.now().isoformat()})
            return {"likes": v["likes"], "dislikes": v["dislikes"], "message": "Liked"}
    for v in quick_videos_db:
        if v["id"] == video_id:
            v["likes"] += 1
            likes_db.append({"user_id": user_id, "video_id": video_id, "created_at": datetime.now().isoformat()})
            return {"likes": v["likes"], "dislikes": v["dislikes"], "message": "Liked"}
    raise HTTPException(404, "Video not found")

@app.post("/api/videos/{video_id}/dislike")
def dislike_video(video_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    if has_disliked(user_id, video_id):
        raise HTTPException(400, "You already disliked this video")
    if has_liked(user_id, video_id):
        for i, l in enumerate(likes_db):
            if l["user_id"] == user_id and l["video_id"] == video_id:
                likes_db.pop(i)
                for v in videos_db:
                    if v["id"] == video_id:
                        v["likes"] = max(0, v["likes"] - 1)
                        break
                for v in quick_videos_db:
                    if v["id"] == video_id:
                        v["likes"] = max(0, v["likes"] - 1)
                        break
                break
    for v in videos_db:
        if v["id"] == video_id:
            v["dislikes"] += 1
            dislikes_db.append({"user_id": user_id, "video_id": video_id, "created_at": datetime.now().isoformat()})
            return {"likes": v["likes"], "dislikes": v["dislikes"], "message": "Disliked"}
    for v in quick_videos_db:
        if v["id"] == video_id:
            v["dislikes"] += 1
            dislikes_db.append({"user_id": user_id, "video_id": video_id, "created_at": datetime.now().isoformat()})
            return {"likes": v["likes"], "dislikes": v["dislikes"], "message": "Disliked"}
    raise HTTPException(404, "Video not found")

@app.get("/api/videos/{video_id}/has_liked")
def check_liked(video_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        return {"liked": False, "disliked": False}
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        return {"liked": False, "disliked": False}
    return {"liked": has_liked(user_id, video_id), "disliked": has_disliked(user_id, video_id)}

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    for i, v in enumerate(videos_db):
        if v["id"] == video_id:
            if v["uploader_id"] != user_id:
                raise HTTPException(403, "You can only delete your own videos")
            file_path = v.get("file_path", f"{UPLOAD_DIR}/{video_id}.mp4")
            if os.path.exists(file_path):
                os.remove(file_path)
            videos_db.pop(i)
            return {"message": "Video deleted"}
    for i, v in enumerate(quick_videos_db):
        if v["id"] == video_id:
            if v["uploader_id"] != user_id:
                raise HTTPException(403, "You can only delete your own videos")
            file_path = v.get("file_path", f"{QUICK_DIR}/{video_id}.mp4")
            if os.path.exists(file_path):
                os.remove(file_path)
            quick_videos_db.pop(i)
            return {"message": "Video deleted"}
    raise HTTPException(404, "Video not found")

# --- КОММЕНТАРИИ ---
@app.post("/api/videos/{video_id}/comments")
def add_comment(video_id: str, comment: CommentCreate, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    global comment_counter
    new_comment = {"id": comment_counter, "video_id": video_id, "text": comment.text, "author_id": user_id, "author_name": user["username"], "likes": 0, "created_at": datetime.now().isoformat()}
    comments_db.append(new_comment)
    comment_counter += 1
    return new_comment

@app.get("/api/videos/{video_id}/comments")
def get_comments(video_id: str):
    video_comments = [c for c in comments_db if c["video_id"] == video_id]
    video_comments.sort(key=lambda x: x["created_at"], reverse=True)
    return video_comments

@app.post("/api/comments/{comment_id}/like")
def like_comment(comment_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    for c in comments_db:
        if c["id"] == comment_id:
            c["likes"] += 1
            return {"likes": c["likes"]}
    raise HTTPException(404, "Comment not found")

@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    global comments_db
    for i, c in enumerate(comments_db):
        if c["id"] == comment_id:
            if c["author_id"] != user_id:
                raise HTTPException(403, "You can only delete your own comments")
            comments_db.pop(i)
            return {"message": "Comment deleted"}
    raise HTTPException(404, "Comment not found")

@app.get("/api/channel/{username}")
def get_channel(username: str):
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, "Channel not found")
    user_videos = [v for v in videos_db if v["uploader_name"] == user["username"]]
    user_quick = [v for v in quick_videos_db if v["uploader_name"] == user["username"]]
    return {
        "id": user["id"],
        "channel_name": user["channel_name"],
        "username": user["username"],
        "channel_description": user.get("channel_description", ""),
        "channel_cover": user.get("channel_cover"),
        "subscribers_count": user.get("subscribers_count", 0),
        "videos": user_videos,
        "quick_videos": user_quick
    }

# --- ИСТОРИЯ ---
@app.get("/api/history")
def get_watch_history(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    history = [h for h in watch_history_db if h["user_id"] == user_id]
    history.sort(key=lambda x: x["watched_at"], reverse=True)
    return {"history": history}

@app.delete("/api/history")
def clear_history(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    global watch_history_db
    watch_history_db = [h for h in watch_history_db if h["user_id"] != user_id]
    return {"message": "History cleared"}

# --- УВЕДОМЛЕНИЯ ---
@app.get("/api/notifications")
def get_notifications(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user_notifications = [n for n in notifications_db if n["user_id"] == user_id]
    user_notifications.sort(key=lambda x: x["created_at"], reverse=True)
    return {"notifications": user_notifications}

@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    for n in notifications_db:
        if n["id"] == notification_id and n["user_id"] == user_id:
            n["read"] = True
            return {"message": "Marked as read"}
    raise HTTPException(404, "Notification not found")

@app.get("/api/notifications/unread_count")
def get_unread_count(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        return {"count": 0}
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        return {"count": 0}
    count = sum(1 for n in notifications_db if n["user_id"] == user_id and not n["read"])
    return {"count": count}

# ========== СУБТИТРЫ ==========
import os
from fastapi.responses import PlainTextResponse

# Хранилище субтитров (временное, в памяти)
subtitles_db = {}

@app.post("/api/videos/{video_id}/subtitles")
async def upload_subtitles(
    video_id: str,
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    """Загрузка файла субтитров (.vtt) для видео"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    
    # Проверяем, что видео принадлежит пользователю
    video_exists = False
    for v in videos_db + quick_videos_db:
        if v["id"] == video_id and v["uploader_id"] == user_id:
            video_exists = True
            break
    
    if not video_exists:
        raise HTTPException(404, "Video not found or you don't own it")
    
    # Читаем содержимое файла
    content = await file.read()
    subtitles_db[video_id] = content.decode('utf-8')
    
    return {"message": "Subtitles uploaded", "video_id": video_id}

@app.get("/api/videos/{video_id}/subtitles")
async def get_subtitles(video_id: str):
    """Получение субтитров для видео"""
    if video_id in subtitles_db:
        return PlainTextResponse(subtitles_db[video_id], media_type="text/vtt")
    return PlainTextResponse("", status_code=404)
