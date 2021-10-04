from fastapi import FastAPI
from .db import Database
from .models import Thing

app = FastAPI()
db = Database()


@app.get('/')
async def root():
    return {"message": "KernelCI API"}


@app.get('/thing/{thing_id}')
def thing(thing_id: str):
    return {'thing': db.find_by_id(Thing, thing_id)}


@app.get('/things')
def things():
    return {'things': db.find_all(Thing)}


@app.post('/thing')
def create_thing(thing: Thing, token: str = Depends(get_current_user)):
    return {'thing': db.create(thing)}
