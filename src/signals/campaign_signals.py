import aiohttp
import aioredis
from ..utils.db import get_redis
import json
import asyncio
# END IMPORTS


def on_campaign_created(mapper, connection, target):
    print("TARGET: ", target)
    asyncio.create_task(dequeue_contact(target.user_id))


async def dequeue_contact(user_id):
    print("DEQUEUE CALLED..")
    redis: aioredis.Redis = await get_redis()
    contact_json = await redis.lpop(f"user_id:{user_id}:contact_queue")
    print("CONTACT JSON: ", contact_json)
    if contact_json is not None:
        contact = json.loads(contact_json)
        print("CONTACT: ", contact)
        url = f"http://127.0.0.1:8000/make-call/{contact['phone_number']}"
        headers = {
            "Authorization": f"Bearer {contact['access_token']}",
            "Content-Type": "application/json",
        }
        data = {
            "agent_name": contact['agent_name'],
            "greeting": contact['greeting_message'],
            "role": contact['role_of_bot'],
            "industry": contact['industry'],
            "receiver_name": contact['target_first_name'],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                print("AFTER CALLING API..")
                if response.status == 200:
                    print("Success! Response..")
                else:
                    print("Error! Status code..")
    else:
        print("CONTACT JSON IS NONE..")
        return False
