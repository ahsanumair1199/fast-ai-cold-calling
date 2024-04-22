from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.voice_call import voice_router
from .routers.user import user_router
from .routers.voices import voices_router
from .routers.campaign import campaign_router
from .utils.db import engine
from sqlmodel import SQLModel
from .constants.common import API_TITLE, API_VERSION, API_DESCRIPTION
# END IMPORTS

# APP CONFIG
app = FastAPI(title=API_TITLE, description=API_DESCRIPTION,
              version=API_VERSION)

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event('startup')
def startup():
    SQLModel.metadata.create_all(engine)


# API ROUTES
app.include_router(voice_router)
app.include_router(user_router)
app.include_router(voices_router)
app.include_router(campaign_router)
