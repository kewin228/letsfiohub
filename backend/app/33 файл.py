from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# Добавьте модели данных
class Video(BaseModel):
    id: str
    title: str
    description: str
    url: str

# Временное хранилище видео
videos_db = []

# Добавьте новые эндпоинты
@app.post("/api/v1/videos")
def create_video(video: Video):
    videos_db.append(video)
    return {"message": "Video created", "video": video}

@app.get("/api/v1/videos/{video_id}")
def get_video(video_id: str):
    for video in videos_db:
        if video.id == video_id:
            return video
    raise HTTPException(status_code=404, detail="Video not found")