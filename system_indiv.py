import aiohttp
import asyncio
import time, copy, pickle
import numpy as np
import json, sys, os, tqdm
import requests
import threading
import subprocess
from sklearn.model_selection import GridSearchCV, ParameterGrid
import gym
from gym.spaces import Box, Discrete

from functions import *
# from parameters import *
from system_config_indiv import *

np.set_printoptions(precision=3, suppress=True)

MAX_RBG = 16 # 10MHz , 3RB per RBG, so 1683 = 48 for DL 
RBS = 50

TIME_INTERVAL = 60 # seconds
SERVERS = ["vir-oai-spgwu-1", "vir-oai-spgwu-2", "vir-oai-spgwu-3",] # comp servers' name, e.g., server1 server2
SERVERS_ADDR = ["http://127.0.0.1:10001/", "http://127.0.0.1:10002/", "http://127.0.0.1:10003/",] # comp servers' name, e.g., server1 server2


HEADERS = {
'Accept': "application/json",
'Content-Type': "application/json",
# 'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
}

ADDR_CN = 'http://192.168.17.4:8888/'
ADDR_TN = 'http://127.0.0.1:7777/'
ADDR_AN = 'http://127.0.0.1:9999/'


class AN_SLICE_CONF:
    def __init__(self, an_rb_ul=10, an_sche_alg_ul=0, an_maxmcs_ul=0, an_rb_dl=10, an_sche_alg_dl=0, an_maxmcs_dl=0):
        self.an_rb_ul = an_rb_ul
        self.an_sche_alg_ul = an_sche_alg_ul
        self.an_maxmcs_ul = an_maxmcs_ul
        self.an_rb_dl = an_rb_dl
        self.an_sche_alg_dl = an_sche_alg_dl
        self.an_maxmcs_dl = an_maxmcs_dl

class TN_SLICE_CONF:
    def __init__(self, tn_bw=10, tn_static_path=0):
        self.tn_bw = tn_bw
        self.tn_static_path = tn_static_path

# class CN_SLICE_CONF:
#     def __init__(self, cn_imsi="222010000000001", cn_addr="192.168.17.11"):
#         self.cn_imsi = cn_imsi
#         self.cn_addr = cn_addr

class CP_SLICE_CONF:
    def __init__(self, cp_cpu=1.0, cp_ram=1000):
        self.cp_cpu = cp_cpu
        self.cp_ram = cp_ram
        # self.cp_bio = cp_bio

class SYS:
    def __init__(self,  num_vars=6, num_obs=11, idx=0, traffic=1, seeds=0,):
        self.idx = idx
        self.num_vars = num_vars
        self.slice_traffic = traffic
        self.itime = 0
        np.random.seed(seeds) # for the traffic generation 

        self.observation_space = Box(-1000.0, 1000.0, (num_obs,))
        self.action_space = Box(0.0, 1.0, (num_vars,))
        
        self.sleep_time = TIME_INTERVAL # second after action

        # prepare some data before sending resource orchestration
        self.loop = asyncio.get_event_loop()

        # not initialize the system everytime, FlexRAN will get confused! run initialization_system.py ONCE

        # start background thread to continuously update reliability data from RAN side
        t1 = threading.Thread(target = self.GET_AN_STATS)
        t1.setDaemon(True)
        t1.start()
    
    def reset(self,):
        # do nothing
        self.itime = 0

        # inform user the traffic
        self.inform_traffic()
        
        return []

    def modify_an_conf(self, an_slice_conf, CONF):
        start_ul_rb = 3  # XXX the first and last 3 RB in UL is reserved, see FlexRAN
        end_ul_rb = RBS - 3  # XXX the first and last 3 RB in UL is reserved, see FlexRAN
        start_dl_rb = 0
        end_dl_rb = MAX_RBG # XXX RBG in DL, see FlexRAN

        # update ul
        for idx in range(len(CONF["ul"]["slices"])):
            slice_conf = CONF["ul"]["slices"][idx]
            slice_id = slice_conf["id"]
            if slice_id == 0:
                slice_conf["scheduler"] = UL_SCHER[min(max(an_slice_conf.an_sche_alg_ul, 0), 0)]
                slice_conf["maxmcs"] = max(an_slice_conf.an_maxmcs_ul, 0)
                slice_conf["static"]["posLow"] = min(max(start_ul_rb, 0), end_ul_rb)
                slice_conf["static"]["posHigh"] = min(max(start_ul_rb + an_slice_conf.an_rb_ul - 1, 0), end_ul_rb)
                start_ul_rb = start_ul_rb + an_slice_conf.an_rb_ul # inclusive, so plus 1

        # update dl
        for idx in range(len(CONF["dl"]["slices"])):
            slice_conf = CONF["dl"]["slices"][idx]
            slice_id = slice_conf["id"]
            if slice_id == 0:
                slice_conf["scheduler"] = DL_SCHER[min(max(an_slice_conf.an_sche_alg_dl, 0), 2)]
                slice_conf["maxmcs"] = max(an_slice_conf.an_maxmcs_dl, 0)
                slice_conf["static"]["posLow"] = min(max(start_dl_rb, 0), end_dl_rb)
                slice_conf["static"]["posHigh"] = min(max(start_dl_rb + an_slice_conf.an_rb_dl - 1, 0), end_dl_rb)
                start_dl_rb = start_dl_rb + an_slice_conf.an_rb_dl # inclusive, so plus 1

        return CONF

    def modify_tn_conf(self, tn_slice_conf, CONF):

        for key, val in CONF.items():
            slice_id = int(key[-1])
            if slice_id == 0:
                for skey, sval in val.items():
                    sval["bandwidth"] = tn_slice_conf.tn_bw
                    sval["static_path"] = tn_slice_conf.tn_static_path

        return CONF


    # def modify_cn_conf(self, cn_slice_conf, CONF):

    #     CONF["IMSI"] = cn_slice_conf.cn_imsi
    #     CONF["ADDR"] = cn_slice_conf.cn_addr

    #     return CONF

    
    # async def NOTIFY_AN_SLICE_ASSOCIATION(self, CONF):

    #     async with aiohttp.ClientSession() as session:
            
    #         payload = json.dumps(CONF)
    #         # send to an
    #         content, _ = await POST(session, ADDR_AN+'slice/enb/-1', payload)
    #         time.sleep(1)

    #         for key, CONF_UE in CONF_UES.items():
                
    #             # directly send raw data, since "[]" is not easy to convert with json
    #             content, _ = await POST(session, ADDR_AN+'auto_ue_slice_assoc/enb/-1/slice/'+key, '["'+CONF_UE['imsi']+'"]')
    #             time.sleep(1)

    # async def NOTIFY_CN_SLICE_ASSOCIATION(self, CONFS):

    #     async with aiohttp.ClientSession() as session:
    #         ######################## CN #################################
    #         # modify cn conf
    #         for cn_slice_conf in CONFS: # for each CN, we send one time

    #             payload = json.dumps(cn_slice_conf)
    #             # send to cn
    #             content, _ = await PUT(session, ADDR_CN, payload)
    #             time.sleep(1)

    def GET_AN_STATS(self,):
        time.sleep(1)  # wait the configuration in RAN to be done
        command = 'docker stats --format "{{.Container}}: {{.CPUPerc}}" ' + SERVERS[0]
        popen = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE, universal_newlines=True)
        while True: # infinite loop to update info
            try:
                json_stats = requests.get(ADDR_AN+'stats/').json()
                # print('.', end='')
    
                for key, CONF_UE in CONF_UES.items():
                    # for each user, get the stats

                    try: # sometimes maybe nothing there
                        json_ue_config = json_stats['eNB_config'][0]['UE']['ueConfig'] # here is a list of ue

                        for val in json_ue_config:
                            # directly send raw data, since "[]" is not easy to convert with json
                            if CONF_UE['imsi'] == val['imsi']: 
                                CONF_UE['rnti'] = val['rnti'] ## assign rnti new 
                    except: pass

                    # update retx info
                    try: # sometimes maybe nothing there
                        ue_mac_stats = json_stats['mac_stats'][0]['ue_mac_stats'] # this 0 is for enb index
                        for ue in ue_mac_stats:
                            if CONF_UE['rnti'] == ue['rnti']: 
                                # calculation of reliability # here 1000 means 1 second to 1000 ms 
                                reliable_dl = 1 - (ue['mac_stats']['macStats']['totalPrbRetxDl'] - CONF_UE['retx_dl'])/((time.time() - CONF_UE['last_time'])*RBS*1000)
                                reliable_ul = 1 - (ue['mac_stats']['macStats']['totalPrbRetxUl'] - CONF_UE['retx_ul'])/((time.time() - CONF_UE['last_time'])*RBS*1000)
                                CONF_UE['reliability_ul'].append(reliable_ul)
                                CONF_UE['reliability_dl'].append(reliable_dl) # reliable retran packet num
                                load_dl = (ue['mac_stats']['macStats']['totalPrbDl'] - CONF_UE['total_dl'])/((time.time() - CONF_UE['last_time'])*RBS*1000)
                                load_ul = (ue['mac_stats']['macStats']['totalPrbUl'] - CONF_UE['total_ul'])/((time.time() - CONF_UE['last_time'])*RBS*1000)
                                CONF_UE['load_dl'].append(load_dl)
                                CONF_UE['load_ul'].append(load_ul)  # load, used prb num
                                CONF_UE['mcs_dl'].append(ue['mac_stats']['macStats']['mcs1Dl'])
                                CONF_UE['mcs_ul'].append(ue['mac_stats']['macStats']['mcs1Ul']) # radio quality mcs 
                                
                                # update information
                                CONF_UE['retx_dl'] = ue['mac_stats']['macStats']['totalPrbRetxDl']
                                CONF_UE['retx_ul'] = ue['mac_stats']['macStats']['totalPrbRetxUl']
                                CONF_UE['total_ul'] = ue['mac_stats']['macStats']['totalPrbUl']
                                CONF_UE['total_dl'] = ue['mac_stats']['macStats']['totalPrbDl']
                                CONF_UE['last_time'] = time.time()

                    except: pass
            except:
                print('FlexRAN controller down...')
                pass
            ############## get docker stats
            try:
                outputs = [popen.stdout.readline() for _ in range(self.num_slice)]
                workload = [float(out.split(':')[-1].split('%')[0]) for out in outputs] # percent
                for key, CONF_UE in CONF_UES.items():
                    CONF_UE['workload'] = workload[int(key)] # the slice id
            except:
                # popen = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE, universal_newlines=True)    
                for key, CONF_UE in CONF_UES.items():
                    CONF_UE['workload'] = 0.0 # the slice id

            # print(json.dumps(CONF_UES, indent=4, sort_keys=True))
            # print('-'*80)

            time.sleep(1) # sleep for 1 second

    def handle_exception(self,):
        pass
        # raise ValueError("system error detected!")

    async def notify_domain_managers(self, an_slice_confs, tn_slice_confs, cp_slice_confs):

        async with aiohttp.ClientSession() as session:
            
            ######################## AN #################################
            # modify an conf
            CONF = self.modify_an_conf(an_slice_confs, copy.deepcopy(CONF_AN)) 

            payload = json.dumps(CONF)
            # send to an  XXX may be double comfirm because overlap exist w.r.t. before
            content, idx = await POST(session, ADDR_AN+'slice/enb/-1', payload)
            time.sleep(0.1)
            if idx is False: self.handle_exception()

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            ######################## TN #################################
            # modify tn conf
            CONF = self.modify_tn_conf(tn_slice_confs, copy.deepcopy(CONF_TN)) 

            payload = json.dumps(CONF)
            # send to tn
            content, idx = await PUT(session, ADDR_TN, payload)

            if idx is False: self.handle_exception()

        ######################## COMP #################################
        # modify cp conf

        # cp_slice_confs.cp_cpu = np.clip(int(100*cp_slice_confs.cp_cpu)/100, 0.1, 1) # here, 100 is for control the precision
        ## attention XXX base_cpu for showing the differences
        bashCommand = "docker update --cpus=" + str(cp_slice_confs.cp_cpu) + " " + SERVERS[0]
        print(bashCommand)
        subprocess.call(bashCommand, shell=True, stdout=subprocess.PIPE)
        time.sleep(0.1)

        return True # if everything good

    def inform_traffic(self,): # inform traffic to users
        # give the traffic trace info to each slice at here # TODO how to scale traffic for slice
        reply = requests.put(SERVERS_ADDR[self.idx], data={ "traffic": str(self.slice_traffic)})
        # print('traffic: ', tmp, flush=True)


    # def get_reliability(self,):
    #     reliability_ul, reliability_dl = [0,0,0], [0,0,0]

    #     # get all reliability from background updated global variable
    #     for key, CONF_UE in CONF_UES.items():
    #         useful_len = int(len(CONF_UE['reliability_ul'])*0.5)
    #         reliability_ul[int(key)] = CONF_UE['reliability_ul']
    #         reliability_dl[int(key)] = CONF_UE['reliability_dl']
    #         CONF_UE['reliability_ul'] = [1] # reset 
    #         CONF_UE['reliability_dl'] = [1] # reset 
        
    #     return reliability_ul, reliability_dl

    def retrieve_indiv_performance(self):

        reply = requests.get(SERVERS_ADDR[self.idx])
        stats = json.loads(reply.text)

        # get all reliability from background updated global variable 
        # TODO XXX here, always "str(0)" because indiv system only conects single user
        reliability_ul = CONF_UES[str(0)]['reliability_ul']
        reliability_dl = CONF_UES[str(0)]['reliability_dl']
        
        CONF_UES[str(0)]['reliability_ul'] = [1] # reset 
        CONF_UES[str(0)]['reliability_dl'] = [1] # reset 
        
        return np.array(stats["performance"]), np.array(stats["queuesize"]), np.array(stats["computetime"]), reliability_ul, reliability_dl

    def action_to_conf(self, action):
        # URBG, UMCS, DRBG, DMCS, TNBW, CCPU
        an_slice_conf = AN_SLICE_CONF()
        tn_slice_conf = TN_SLICE_CONF()
        cp_slice_conf = CP_SLICE_CONF()
        an_slice_conf.an_rb_ul       = int(np.clip(action[0]*40+3, 3, 43)) # RB  in UL XXX
        an_slice_conf.an_sche_alg_ul = 0 # only one ul alg
        an_slice_conf.an_maxmcs_ul   = 10 - int(np.clip(action[1]*10, 0, 10)) #
        an_slice_conf.an_rb_dl       = int(np.clip(action[2]*13+1, 1, 14)) # RBG in DL XXX 
        an_slice_conf.an_sche_alg_dl = 0
        an_slice_conf.an_maxmcs_dl   = 10 -  int(np.clip(action[3]*10, 0, 10)) # attention XXX here mcs is minus
        tn_slice_conf.tn_bw          = int(np.clip(action[4]*90+3, 3, 93))
        cp_slice_conf.cp_cpu         = float(np.clip(int(action[5]*100)/100+0.3, 0.3, 1.3))
        print(an_slice_conf.an_rb_ul, an_slice_conf.an_maxmcs_ul, an_slice_conf.an_rb_dl, an_slice_conf.an_maxmcs_dl, tn_slice_conf.tn_bw, cp_slice_conf.cp_cpu)
        return [an_slice_conf, tn_slice_conf, cp_slice_conf]

    # def get(self, ):
    #     performance, reliability = self.retrieve_performance()
    #     return performance, reliability

    def limit_action(self, action):

        action = np.clip(action, 0, 1)

        return action
        
    def enforce_idx(self, action):

        all_confs = self.action_to_conf(action) 

        an_slice_confs = all_confs[0]
        tn_slice_confs = all_confs[1]
        cp_slice_confs = all_confs[2]

        # send actual resource orchestration
        self.loop.run_until_complete(self.notify_domain_managers(an_slice_confs, tn_slice_confs, cp_slice_confs))

    def step(self, action):
        """
        take action, implement to system, get performance
        order is: URBG, UMCS, DRBG, DMCS, TNBW, CCPU
        """
        action = np.clip(action, 0, 1) # limit at the beginning

        # enforce the action to system
        self.enforce(action) 

        # wait for a while
        time.sleep(self.sleep_time)

        # get the resulted performance
        performance, reliability = self.retrieve_performance()
        
        # inform user the traffic
        self.inform_traffic() 

        # get network state [ traffic, network state (radio quality, RAN load, COMP workload), user state (perf)]
        state = self.build_state()

        # return state, performance, False, reliability
        return np.array(state), np.array(reward), done, np.array(cost)
    
    def build_state(self,):
        states = []
        
        return states

############################################## run  ########################################################
# each time, measure a slice, slice 1 --> vir-spgw-u-1, slice 2 --> vir-spgw-u-2


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--idx', type=int, default=0)   # slice id        
    parser.add_argument('--traffic', type=int, default=1)     # slice traffic
    parser.add_argument('--mode', type=str, default="grid")
    args = parser.parse_args()

    start_time = time.time()

    # URBG, UMCS, DRBG, DMCS, TNBW, CCPU
    #  0     1     2     3     4     5  
    MAP = dict(URBG=0, UMCS=1, DRBG=2, DMCS=3, TNBW=4, CCPU=5, )
    sys = SYS(idx=args.idx, traffic=args.traffic, num_vars=len(MAP)) # create the sys class
    sys.reset()

    ################################################################################################################
    ################################################################################################################
    ################################################################################################################
    if args.mode == "indiv":
        # this is for single application measurement, TODO XXX Be sure to change idx to 0 for getting reliability stats when only one phone connects to the testbed
        performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance()
        time.sleep(120)
        performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance()
        pickle.dump({"performance":performance, "queuesz":queuesz, "computetime":computetime, "reliability_ul":reliability_ul, "reliability_dl":reliability_dl}, open( "app_eval/measurement_system_performance_slice_"+str(args.idx)+"_traffic_"+str(args.traffic)+".pickle", "wb" ))

        print('performance', np.mean(performance), np.std(performance), 'computetime', np.mean(computetime), np.std(computetime), 'reliability', np.mean(reliability_ul), np.mean(reliability_dl))
        print('indiviudal measurement is done')
    
    
    ################################################################################################################
    ################################################################################################################
    ################################################################################################################
    if args.mode == "grid":
        # this is for grid searching under different 
        VARIABLES = [  {"URBG":np.arange(0.1, 1.01, 0.2), \
                        "CCPU":np.arange(0.1, 1.01, 0.2), \
                        }, # MAR
                    {"DRBG":np.arange(0.1, 1.01, 0.2), \
                        "TNBW":np.arange(0.1, 1.01, 0.2), \
                        }, # Video
                    {"UMCS":np.arange(0.1, 1.01, 0.2), \
                        "DMCS":np.arange(0.1, 1.01, 0.2), \
                        }  # IoT
                    ]
        
        grid = ParameterGrid(VARIABLES[args.idx])
        print("grid search length:", len(grid))
        
        RESULTS = []

        for idx in range(len(grid)):

            # try: 
            #     RESULTS = pickle.load(open("app_eval/measurement_grid_search_slice_"+str(args.idx)+".pickle", "rb" ))
            # except: pass

            # get params
            params = grid[idx]
            # init action, single vector
            action = np.ones(sys.action_space.shape) # 0.1 as default, attention XXX this should be ONE for other resources
            # assign to action
            for key, val in params.items():
                action[MAP[key]] = val
            # run the system
            print('ite: ', idx, 'action is', action)
            sys.enforce_idx(np.array(action))

            # this two line codes is to eliminate the previous affects, e.g., unfinished queuing tasks
            time.sleep(10)
            performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance()

            # this is for real performance collection
            time.sleep(TIME_INTERVAL)
            performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance()
            
            print('-'*40)
            print(params, np.mean(performance), np.mean(reliability_ul), np.mean(reliability_dl))
            print('-'*40)

            RESULTS.append({"performance":performance, "queuesz":queuesz, "computetime":computetime, "reliability_ul":reliability_ul, "reliability_dl":reliability_dl})

            pickle.dump(RESULTS, open("app_eval/measurement_system_grid_search_slice_"+str(args.idx)+".pickle", "wb" ))

        print('grid search measurement completed!')

    raise ValueError('make sure you set the correct mode, e.g., indiv or grid.')
    ################################################################################################################
    ################################################################################################################
    ################################################################################################################
    # for idx in range(len(grid)):

    #     try: 
    #         RESULTS = pickle.load(open("app_eval/measurement_grid_search_sim_slice_"+str(args.idx)+".pickle", "rb" ))
    #     except: pass

    #     # get params
    #     params = grid[idx]
    #     # init action, single vector
    #     action = np.zeros(sys.action_space.shape) # 0.1 as default
    #     # assign to action
    #     for key, val in params.items():
    #         action[MAP[key]] = val
    #     # run the system

    #     sys.enforce_idx(np.array(action))

    #     time.sleep(30)

    #     performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance()
        
    #     print('-'*40)
    #     print(params, np.mean(performance), np.mean(reliability_ul), np.mean(reliability_dl))
    #     print('-'*40)

    #     RESULTS.append({"performance":performance, "queuesz":queuesz, "computetime":computetime, "reliability_ul":reliability_ul, "reliability_dl":reliability_dl})

    #     pickle.dump(RESULTS, open("app_eval/measurement_grid_search_sim_slice_"+str(args.idx)+".pickle", "wb" ))

    # print("total measurement time is: ", time.time() - start_time)
    # print('measurement completed!')

    # pickle.dump(RESULTS, open( "measurement_save_MAR.pkl", "wb" ))