import aiohttp
import asyncio
import time, copy, pickle
import numpy as np
import json, sys, os, tqdm
import requests
import threading
import subprocess

from functions import *
from system_config_indiv import *

ADDR_CN = 'http://192.168.17.4:8888/'
ADDR_TN = 'http://127.0.0.1:7777/'
ADDR_AN = 'http://127.0.0.1:9999/'

# async def get_domain_managers():

#     async with aiohttp.ClientSession(headers=HEADERS) as session:

#         content = await GET(session, ADDR_AN+'stats_manager/')

#         content = await GET(session, ADDR_TN)

#         content = await GET(session, ADDR_CN)


async def NOTIFY_AN_SLICE_ASSOCIATION(CONF):

    async with aiohttp.ClientSession() as session:
        
        payload = json.dumps(CONF)
        # send to an
        content, _ = await POST(session, ADDR_AN+'slice/enb/-1', payload)
        print(content)
        time.sleep(1)

        for key, CONF_UE in CONF_UES.items():
            
            # directly send raw data, since "[]" is not easy to convert with json
            content, _ = await POST(session, ADDR_AN+'auto_ue_slice_assoc/enb/-1/slice/'+key, '["'+CONF_UE['imsi']+'"]')
            print(content)
            time.sleep(1)

async def NOTIFY_CN_SLICE_ASSOCIATION(CONFS):

    async with aiohttp.ClientSession() as session:
        ######################## CN #################################
        # modify cn conf
        for cn_slice_conf in CONFS: # for each CN, we send one time

            payload = json.dumps(cn_slice_conf)
            # send to cn
            content, _ = await PUT(session, ADDR_CN, payload)
            print(content)
            time.sleep(1)


# prepare some data before sending resource orchestration
loop = asyncio.get_event_loop()

# loop.run_until_complete(get_domain_managers())


loop.run_until_complete(NOTIFY_CN_SLICE_ASSOCIATION(CONF_CN))


loop.run_until_complete(NOTIFY_AN_SLICE_ASSOCIATION(CONF_AN))


    