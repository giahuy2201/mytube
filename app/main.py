from concurrent.futures import thread
from typing import Union
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import threading
import yt_dlp

import crud, models, schemas
from database import SessionLocal, engine
import downloader
import manager

models.Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/videos", response_model=list[schemas.Video])
def get_videos(db: Session = Depends(get_db), term: str = ''):
    # Retrieve all requested videos
    if term != '':
        videos = crud.search_videos(db,term)
    else:
        videos = crud.get_videos(db)
    return videos


@app.get("/info/{id}")
def get_info(id: str):
    result = "error"
    try:
        result = downloader.download_metadata("https://youtu.be/{}".format(id))
    except yt_dlp.utils.DownloadError as e:
        result = str(e)
    return result


@app.post("/videos", response_model=schemas.Video)
def add_request(request: schemas.VideoCreate, db: Session = Depends(get_db)):
    # fetch metadata
    try:
        video_metadata = downloader.download_metadata(request.url)
    except yt_dlp.utils.DownloadError as e:
        return str(e)
    video = crud.create_video(db, video_metadata)
    # send url to downloader and return immediate result
    t = threading.Thread(
        target=downloader.download_video, args=(request.url, request.preset)
    )
    t.start()
    print("thread {} started".format(t.name))
    return video


@app.get("/download")
def download_file(id: str):
    # send url to downloader and return immediate result
    return manager.getFile(id)
