
import aiohttp
import asyncio
import time, copy, json

import requests


HEADERS = {
'Accept': "application/json",
'Content-Type': "application/json",
# 'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
}

CONF_TN = {
    'slice0':{
                '192.168.17.11':{
                    'bandwidth':10,
                    'static_path':0
                }
            },
}

ADDR_TN = 'http://127.0.0.1:7777/'


def modify_tn_conf(tn_slice_conf, CONF):

    for key, val in CONF.items():
        slice_id = int(key[-1])
        if slice_id == 0:
            for skey, sval in val.items():
                sval["bandwidth"] = tn_slice_conf.tn_bw
                sval["static_path"] = tn_slice_conf.tn_static_path

    return CONF

class TN_SLICE_CONF:
    def __init__(self, tn_bw=10, tn_static_path=0):
        self.tn_bw = tn_bw
        self.tn_static_path = tn_static_path

tn_slice_confs = TN_SLICE_CONF()

def handle_response(response):

    if response.status<200 or response.status>299: 
        # print(",", end="")
        idx = False
    else:
        # print(".", end="")
        idx = True
    return idx

async def PUT(session, addr, payload):

    async with session.put(addr, data=payload) as response:

        idx = handle_response(response)

        html = await response.text()

        return html, idx


async def main():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        ######################## TN #################################
        # modify tn conf
        CONF = modify_tn_conf(tn_slice_confs, copy.deepcopy(CONF_TN)) 

        payload = json.dumps(CONF)
        # send to tn
        content, idx = await PUT(session, ADDR_TN, payload)

        print(content, idx)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

print('done')





# async with aiohttp.ClientSession(headers=headers) as session:
#     async with session.get("http://httpbin.org/headers") as response:
#         json_body = await response.json()






