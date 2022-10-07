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
from system_config import *

np.set_printoptions(precision=3, suppress=True)

MAX_RBG = 25 # 20MHz
RBS = 100

TRAFFIC_SCALE = [5, 2, 100] # mar ul cannot be too large, otherwise crush ul transmission
TIME_INTERVAL = 1 # seconds
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


class baseline_policy:
    def __init__(self, num_slice=3, num_var=8, num_obs=11, id=None):
        self.id = id
        self.num_slice = num_slice
        self.num_var = num_var
        self.num_obs = num_obs
        self.min_res = 0.15
        self.static_conf =self.min_res*np.ones((num_slice, num_var),dtype=np.float32)
        self.static_conf[0,0] = 0.4
        self.static_conf[0,6] = 0.4
        self.static_conf[0,8] = 0.4
        self.static_conf[1,3] = 0.8
        self.static_conf[1,6] = 0.8
        self.static_conf[2,2] = 0.4
        self.static_conf[2,5] = 0.4
        self.traffic = [0,0,0]

    def step(self, observation):
        try: observation = observation.detach().numpy()
        except: pass
        if len(observation) == self.num_obs:
            assert(self.id is not None)
            # self.traffic = observation[1] # traffic at the second position
            action = np.clip(self.static_conf[self.id] * observation[1] / TRAFFIC_SCALE[self.id], self.min_res, 1.0)
            return np.clip(action, 0, 1)
        else:
            obs_mat = np.reshape(observation, (self.num_slice, self.num_obs))
            # the second value is the slice traffic
            self.traffic = [obs_mat[i][1] / TRAFFIC_SCALE[i] for i in range(self.num_slice)]
            action = np.clip([self.static_conf[i] * self.traffic[i] for i in range(self.num_slice)], self.min_res, 1.0) # min 0.1
            return np.clip(action, 0, 1)

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
    def __init__(self, num_slice=3, num_vars=10, num_obs=11, max_eplen=24, id=None, seeds=0, fix_traffic=-1,trace_path='final_traffic_trace.pkl'):
        self.id = id # the id used to indicate which slice info will be seen, None means all slices
        self.num_slice = num_slice
        self.num_vars = num_vars
        self.max_eplen = max_eplen
        self.fix_traffic = fix_traffic
        self.itime = 0
        np.random.seed(seeds) # for the traffic generation 
        
        try: # load traffic and scale it 
            with open(trace_path, 'rb') as handler: self.traffic = pickle.load(handler)
            self.traffic = np.array([traf/np.max(traf) for traf in self.traffic])  # scale to 1
            assert(self.traffic.shape[1]%self.max_eplen == 0) # make sure they are no remains
            reorg_traffic, num = [], int(self.traffic.shape[1]/self.max_eplen)
            for traf in self.traffic:
                reorg = np.reshape(traf, (-1, num))
                reorg_traffic.append(np.mean(reorg,axis=-1))

            self.traffic = np.clip(np.array(reorg_traffic), 0.01, 1) # cannot be zeros for mobile users
            # self.traffic = np.clip(self.traffic, 0.01, 1) # cannot be zeros for mobile users
            self.slice_traffic = self.generate_slice_traffic(self.traffic) # scale for different slices
            assert(max_eplen == self.traffic.shape[1]) # make sure the dimension is correct, otherwise reshape is needed
        except:
            raise ValueError("no found traffic trace file!")

        if self.id is not None:
            self.observation_space = Box(-1000.0, 1000.0, (num_obs,))
            self.action_space = Box(0.0, 1.0, (num_vars,))
        else:
            self.observation_space = Box(-1000.0, 1000.0, (num_slice*num_obs,))
            self.action_space = Box(0.0, 1.0, (num_slice*num_vars,))

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

        self.slice_traffic = self.generate_slice_traffic(self.traffic) # scale for different slices
        if self.fix_traffic>0: self.slice_traffic = self.fix_traffic*np.ones_like(self.slice_traffic)

        time.sleep(2) # wait update

        # inform user the traffic
        self.inform_traffic()
        
        state = self.build_state()
        if self.id is not None: 
            state = state[self.id]
        else:
            state = state
        return state

    def generate_slice_traffic(self, traffic):
        slice_traffic = traffic[np.random.randint(0, len(traffic),self.num_slice)] # random choose traffic trace
        slice_traffic = np.array([TRAFFIC_SCALE[i] * traf for i, traf in enumerate(slice_traffic)]) # scale for different slices
        return slice_traffic

    def modify_an_conf(self, an_slice_confs, CONF):
        start_ul_rb = 3  # XXX the first and last 3 RB in UL is reserved, see FlexRAN
        end_ul_rb = RBS - 3  # XXX the first and last 3 RB in UL is reserved, see FlexRAN
        start_dl_rb = 0
        end_dl_rb = MAX_RBG # XXX RBG in DL, see FlexRAN

        for islice in range(len(an_slice_confs)):
            # for a slice
            an_slice_conf = an_slice_confs[islice]

            # update ul
            for idx in range(len(CONF["ul"]["slices"])):
                slice_conf = CONF["ul"]["slices"][idx]
                slice_id = slice_conf["id"]
                if slice_id == islice:
                    slice_conf["scheduler"] = UL_SCHER[min(max(an_slice_conf.an_sche_alg_ul, 0), 0)]
                    slice_conf["maxmcs"] = max(an_slice_conf.an_maxmcs_ul, 0)
                    slice_conf["static"]["posLow"] = min(max(start_ul_rb, 0), end_ul_rb)
                    slice_conf["static"]["posHigh"] = min(max(start_ul_rb + an_slice_conf.an_rb_ul - 1, 0), end_ul_rb)
                    start_ul_rb = start_ul_rb + an_slice_conf.an_rb_ul # inclusive, so plus 1

            # update dl
            for idx in range(len(CONF["dl"]["slices"])):
                slice_conf = CONF["dl"]["slices"][idx]
                slice_id = slice_conf["id"]
                if slice_id == islice:
                    slice_conf["scheduler"] = DL_SCHER[min(max(an_slice_conf.an_sche_alg_dl, 0), 2)]
                    slice_conf["maxmcs"] = max(an_slice_conf.an_maxmcs_dl, 0)
                    slice_conf["static"]["posLow"] = min(max(start_dl_rb, 0), end_dl_rb)
                    slice_conf["static"]["posHigh"] = min(max(start_dl_rb + an_slice_conf.an_rb_dl - 1, 0), end_dl_rb)
                    start_dl_rb = start_dl_rb + an_slice_conf.an_rb_dl # inclusive, so plus 1

        return CONF

    def modify_tn_conf(self, tn_slice_confs, CONF):

        for islice in range(len(tn_slice_confs)):
            # for a slice
            tn_slice_conf = tn_slice_confs[islice]

            for key, val in CONF.items():
                slice_id = int(key[-1])
                if islice == slice_id:
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
        command = 'docker stats --format "{{.Container}}: {{.CPUPerc}}" ' + SERVERS[0] + ' ' + SERVERS[1] + ' ' + SERVERS[2]
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
                popen = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE, universal_newlines=True)    
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
            for _ in range(self.num_slice):
                content, idx = await POST(session, ADDR_AN+'slice/enb/-1', payload)
                # content = await PUT(session, ADDR_AN+'slice/enb/-1', payload)
                time.sleep(0.5)
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
        for idx in range(len(cp_slice_confs)):
            cp_slice_conf = cp_slice_confs[idx]
            # cp_slice_conf.cp_cpu [0.1, 1]
            cp_slice_conf.cp_cpu = np.clip(cp_slice_conf.cp_cpu, 0.1, 1)
            # cp_slice_conf.cp_ram # mega bytes, [4, 1000]
            # cp_slice_conf.cp_ram = np.clip(cp_slice_conf.cp_ram, 100, 1000)
            # cp_slice_conf.cp_bio block io speed weight [0, 1000]
            # cp_slice_conf.cp_bio = np.clip(cp_slice_conf.cp_bio, 0, 1000)
            bashCommand = "docker update --cpus=" + str(cp_slice_conf.cp_cpu) + SERVERS[idx]
            subprocess.call(bashCommand, shell=True, stdout=subprocess.PIPE)
            time.sleep(0.1)

        return True # if everything good

    def inform_traffic(self,): # inform traffic to users
        # give the traffic trace info to each slice at here # TODO how to scale traffic for slice
        tmp = np.zeros(self.num_slice, dtype=np.float)
        for idx in range(self.num_slice):
            slice_traffic = int(100*self.slice_traffic[idx, min(self.itime, self.max_eplen-1)])/100 # the current time traffic
            tmp[idx] = slice_traffic # just for print
            reply = requests.put(SERVERS_ADDR[idx], data={ "traffic": str(slice_traffic)})
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

    def retrieve_indiv_performance(self, idx=0):

        reply = requests.get(SERVERS_ADDR[idx])
        stats = json.loads(reply.text)

        # get all reliability from background updated global variable
        reliability_ul = CONF_UES[str(idx)]['reliability_ul']
        reliability_dl = CONF_UES[str(idx)]['reliability_dl']
        
        CONF_UES[str(idx)]['reliability_ul'] = [1] # reset 
        CONF_UES[str(idx)]['reliability_dl'] = [1] # reset 
        
        return np.array(stats["performance"]), np.array(stats["queuesize"]), np.array(stats["computetime"]), reliability_ul, reliability_dl

    def retrieve_performance(self,):
        avg_performance, avg_queuesz, avg_computetime, avg_reliability_ul, avg_reliability_dl = [], [], [], [], []

        for idx in range(self.num_slice):
            performance, queuesz, computetime, reliability_ul, reliability_dl = self.retrieve_indiv_performance(idx)
            avg_performance.append(np.mean(performance))
            avg_queuesz.append(np.mean(queuesz))
            avg_computetime.append(np.mean(computetime))
            avg_reliability_ul.append(np.mean(reliability_ul))
            avg_reliability_dl.append(np.mean(reliability_dl))
        
        return avg_performance, avg_queuesz, avg_computetime, avg_reliability_ul, avg_reliability_dl # TODO here, previous is two return vaules

    def action_to_conf(self, action):
        # URBG, UMCS, DRBG, DMCS, TNBW, CCPU
        an_slice_conf = AN_SLICE_CONF()
        tn_slice_conf = TN_SLICE_CONF()
        cp_slice_conf = CP_SLICE_CONF()
        an_slice_conf.an_rb_ul       = int(action[0]*40  + 3  ) # RB  in UL XXX
        an_slice_conf.an_sche_alg_ul = 0 # only one ul alg
        an_slice_conf.an_maxmcs_ul   = int(action[1]*10  + 0  ) #
        an_slice_conf.an_rb_dl       = int(action[2]*12  + 1  ) # RBG in DL XXX 
        an_slice_conf.an_sche_alg_dl = 0
        an_slice_conf.an_maxmcs_dl   = int(action[3]*10  + 0  )
        tn_slice_conf.tn_bw          = int(action[4]*90  + 3  )
        cp_slice_conf.cp_cpu         = float(int((action[5]*2.4 + 0.2)*10)/10)
        return [an_slice_conf, tn_slice_conf, cp_slice_conf]

    # def get(self, ):
    #     performance, reliability = self.retrieve_performance()
    #     return performance, reliability

    def limit_action(self, action):

        if action.ndim == 1:
            assert(self.id is not None)
            action_mat = [np.zeros_like(action) for _ in range(self.num_slice)]
            action_mat[self.id] = copy.deepcopy(action)
            action = np.clip(action_mat,0, 1)
        elif action.ndim == 2:
            # limit the action
            sum_res = np.sum(action, axis=0)
            for idx in range(self.num_vars):
                if sum_res[idx] > 1: # here, some actions have no limitation
                    action[:,idx] = 1*action[:,idx]/sum_res[idx]
                else:
                    pass
        else:
            raise ValueError('input action dimension wrong!')

        return action
        
    def enforce(self, action):

        all_confs = [self.action_to_conf(action[i]) for i in range(self.num_slice)]

        an_slice_confs = [all_confs[i][0] for i in range(self.num_slice)]
        tn_slice_confs = [all_confs[i][1] for i in range(self.num_slice)]
        cp_slice_confs = [all_confs[i][2] for i in range(self.num_slice)]

        # send actual resource orchestration
        self.loop.run_until_complete(self.notify_domain_managers(an_slice_confs, tn_slice_confs, cp_slice_confs))

    def calculate_reward(self, action):
        # where the sche alg and mcs allowance is not counted cause not have more usage
        action = np.clip(action, 0, 1)
        action = self.limit_action(action) # in case of 
        reward = -np.sum(action, axis=1)
        return reward

    def step(self, action):
        """
        take action, implement to system, get performance
        order is: URBG, UALG, UMCS, DRBG, DALG, DMCS, TNBW, TPAH, CCPU, CRAM
        order is: URBG, UMCS, DRBG, DMCS, TNBW, CCPU
        """
        action = np.clip(action, 0, 1) # limit at the beginning
        action = self.limit_action(action)

        # enforce the action to system
        self.enforce(action) 

        # wait for a while
        time.sleep(self.sleep_time)

        # get the resulted performance
        performance, reliability = self.retrieve_performance()
        
        # calculate the reward and cost
        reward = self.calculate_reward(action)
        cost = np.clip(np.array([SLICE_REQUIREMENT[0] - performance[0], SLICE_REQUIREMENT[1] - performance[1], SLICE_REQUIREMENT[-1] - 1000*(reliability[-1]-0.999)]), 0, 1)
        # if np.max(cost)>0: print("costs:   ", cost, flush=True) # print cost if not zeros

        self.itime = (self.itime + 1)%self.max_eplen # increase itime # XXX this time increase should be here, before inform_traffic() and build_state()

        # inform user the traffic
        self.inform_traffic() 

        # get network state [ traffic, network state (radio quality, RAN load, COMP workload), user state (perf)]
        state = self.build_state()
        
        if self.id is not None: 
            state = state[self.id] # if specific slice, then get its state
            reward = reward[self.id]
            cost = cost[self.id]
        else: 
            state = state  # otherwise, flatten the state of all slices
            reward = reward  
            cost = cost

        # return state, performance, False, reliability
        return np.array(state), np.array(reward), done, np.array(cost)
    
    def build_state(self,):
        states = []
        for key, CONF_UE in CONF_UES.items():
            slice_id = int(key) # traffic is last time traffic, instead of real this time traffic
            state = np.array([self.itime, self.slice_traffic[slice_id, max(self.itime-1, 0)], \
                              np.mean(CONF_UE['mcs_dl']), np.mean(CONF_UE['mcs_ul']), \
                              np.mean(CONF_UE['load_dl']), np.mean(CONF_UE['load_ul']),  \
                              np.mean(CONF_UE['workload']),])
            states.append(state)
            if CONF_UE['mcs_dl'] == 0 and CONF_UE['mcs_ul'] == 0: self.handle_exception() # this means FlexRAN controller gets wrong
        return states # TODO XXX
############################################## run  ########################################################

if __name__ == '__main__':
    start_time = time.time()

    NAMES = ['mar', 'video', 'iot']
    IDX = 1
    TRAFFIC = 5
    name = NAMES[IDX]

    # URBG, UMCS, DRBG, DMCS, TNBW, CCPU
    #  0     1     2     3     4     5  
    MAP = dict(URBG=0, UMCS=1, DRBG=2, DMCS=3, TNBW=4, CCPU=5, )
    sys = SYS(id=IDX, fix_traffic=TRAFFIC) # create the sys class
    sys.reset()
    # default_action = 0.1*np.ones(sys.action_space.shape)
    # default_action[0,0] = 0.9  # MAR
    # default_action[0,8] = 0.3  # MAR
    # default_action[2,2] = 0.3  # IoT
    performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance(idx=IDX)
    time.sleep(60)
    performance, queuesz, computetime, reliability_ul, reliability_dl = sys.retrieve_indiv_performance(idx=IDX)
    pickle.dump({"performance":performance, "queuesz":queuesz, "computetime":computetime, "reliability_ul":reliability_ul, "reliability_dl":reliability_dl}, open( "measurement_app_perf_slice_"+str(IDX)+"_traffic_"+str(TRAFFIC)+".pickle", "wb" ))

    print(np.mean(performance), np.mean(reliability_ul), np.mean(reliability_dl))
    
    VARIABLES = [  {"URBG":np.arange(0.1, 1.01, 0.2), \
                    "UMCS":np.arange(0.1, 1.01, 0.2), \
                    "TNBW":np.arange(0.1, 1.01, 0.2), \
                    "CCPU":np.arange(0.1, 1.01, 0.2), \
                    }, # MAR
                   {"DRBG":np.arange(0.1, 1.01, 0.2), \
                    "DMCS":np.arange(0.1, 1.01, 0.2), \
                    "TNBW":np.arange(0.1, 1.01, 0.2), \
                    }, # Video
                   {"UMCS":np.arange(0.1, 1.01, 0.2), \
                    "DMCS":np.arange(0.1, 1.01, 0.2), \
                    }  # IoT
                ]
    
    grid = ParameterGrid(VARIABLES[IDX])
    print("grid search length:", len(grid))
    
    RESULTS = []

    for idx in range(len(grid)):

        try: 
            RESULTS = pickle.load(open( "saves/measurement_save_"+name+".pickle", "rb" ))
        except: pass
        # get params
        params = grid[idx]
        # init action, single vector
        action = 0.1*np.ones(sys.action_space.shape) # 0.1 as default
        # assign to action
        for key, val in params.items():
            action[MAP[key]] = val
        # run the system
        _, reward, d, cost = sys.step(action)
        if d: sys.reset()

        if IDX==2: perf = 10000*(sys.last_reli[IDX]-0.999)
        else: perf = sys.last_perf[IDX]

        print('-'*40)
        print(idx, action, reward, cost, perf)
        print('-'*40)

        RESULTS.append({"act":action, "rew":reward, "cot":cost, "pef":perf})

        pickle.dump(RESULTS, open( "saves/measurement_save_"+name+".pickle", "wb" ))



    print("total measurement time is: ", time.time() - start_time)
    print('measurement completed!')

    # pickle.dump(RESULTS, open( "measurement_save_MAR.pkl", "wb" ))