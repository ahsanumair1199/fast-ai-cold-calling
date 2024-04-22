from sqlmodel import create_engine
import aioredis
# END IMPORTS

# SQL
DATABASE_URL = "sqlite:///database.db"
connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

# REDIS


def get_redis():
    return aioredis.from_url("redis://localhost:6379/0")
