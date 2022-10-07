import aiohttp
import asyncio
import time

import requests



headers = {
'Accept': "application/json",
'Content-Type': "application/json",
'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
}

async def main():
    async with aiohttp.ClientSession() as session:
        for _ in range(10):
            async with session.get('http://python.org') as response:

                print("Status:", response.status)
                print("Content-type:", response.headers['content-type'])

                html = await response.text()
                print("Body:", html[:100], "...")

start_time = time.time()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

print(time.time() - start_time)





# async with aiohttp.ClientSession(headers=headers) as session:
#     async with session.get("http://httpbin.org/headers") as response:
#         json_body = await response.json()