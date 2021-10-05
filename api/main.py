from fastapi import FastAPI
from .db import Database

app = FastAPI()
db = Database()


@app.get('/')
async def root():
    return {"message": "KernelCI API"}
