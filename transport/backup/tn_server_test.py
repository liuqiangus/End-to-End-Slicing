import time, os, sys, csv, copy
import threading, socket, ctypes, requests
import numpy as np
from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions

from tn_functions import *

def parse_database(database):
    
    static_users = []
    regular_users = []
    const_hosts = []
    bandwidth = []

    for s_key in database.keys(): # loop for slices
        if s_key[:-1] == 'slice':
            for u_key in database[s_key].keys():  # loop for users
                if database[s_key][u_key]['static_path'] == 1: 
                    static_users.append(u_key)
                else:
                    regular_users.append(u_key)
                    bandwidth.append(database[s_key][u_key]['bandwidth'])
        else:
            for u_key in database[s_key].keys():  # loop for users
                const_hosts.append(u_key)

    # sorted them
    indexs = sorted(range(len(regular_users)), key=regular_users.__getitem__)
    bandwidth = [bandwidth[i] for i in indexs]
    regular_users = [regular_users[i] for i in indexs]
    indexs = sorted(range(len(static_users)), key=static_users.__getitem__)
    static_users = [static_users[i] for i in indexs]

    return static_users, regular_users, bandwidth, const_hosts

#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

hypervisor = FlaskAPI(__name__)

# the slices addrs use target SPGWU address
# the enb addr use enb host src address, Mbps unit
DATABASE = {
    'slice0':{
                '192.168.17.11':{
                    'bandwidth':100,
                    'static_path':0
                }
            },
    'slice1':{
                '192.168.17.12':{
                    'bandwidth':100,
                    'static_path':0
                }
            },
    'slice2':{
                '192.168.17.13':{
                    'bandwidth':100,
                    'static_path':0 
                }
            },
    'default':{
                '10.0.0.100':{
                    'bandwidth':1000,
                    'static_path':1
                }
            },
}

BACKUP = copy.deepcopy(DATABASE) # as backup

INDICATOR = True  # global variable

PRIORITY = MIN_PRIORITY+1  # global variable

#the ruckus switch openflow id #'s' # XXX find the correct switch id XXX
SWITCH_ID = 106225813884292 

PORT_LISTS = [1, 12] # 12 ports in switch, do not broadcast to all ports, that reduces performance

TABLE_ID = 0  # default table id
GROUP_ID = 1  # default broadcast group id for arp flows

user1, user2, _, _ = parse_database(DATABASE) # get default users and bandwidth
ORDERED_USERS = user1 + user2
ORDERED_USERS.sort()
#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

def create_database_with_request(request):
    global DATABASE

    data = request.data # get data from 

    try:
        for s_key in data.keys(): # loop for slices
            if s_key not in DATABASE.keys(): DATABASE[s_key] = {}

            for u_key in data[s_key].keys():  # loop for users
                if u_key not in DATABASE[s_key].keys(): DATABASE[s_key][u_key] = {}

                for c_key in data[s_key][u_key].keys(): # loop for config
                    DATABASE[s_key][u_key][c_key] = data[s_key][u_key][c_key]
        return True
    except:
        return False

def update_database_with_request(request):
    global DATABASE

    data = request.data # get data from 

    try:
        for s_key in data.keys(): # loop for slices
            for u_key in data[s_key].keys():  # loop for users
                for c_key in data[s_key][u_key].keys(): # loop for config
                    if c_key in DATABASE[s_key][u_key].keys(): # if matched, update DATABASE
                        DATABASE[s_key][u_key][c_key] = data[s_key][u_key][c_key]
        return True
    except:
        return False

def delete_database_with_request(request):
    global DATABASE, BACKUP

    DATABASE = copy.deepcopy(BACKUP)

    return True


@hypervisor.route("/", methods=['GET', 'PUT', 'POST', 'DELETE'])
def function():
    """
    List or update DATABASE.
    """
    global DATABASE, SWITCH_ID
    print("-"*40)
    if request.method == 'PUT':
        
        if_success = update_database_with_request(request)

        if if_success:
            static_users, regular_users, bandwidth, _ = parse_database(DATABASE) # get default users and bandwidth
            print("static_users: ", static_users, "regular_users: ", regular_users, "bandwidth: ", bandwidth)

            implement_configuration(SWITCH_ID, static_users, regular_users, bandwidth)

            return DATABASE, status.HTTP_202_ACCEPTED
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST

    elif request.method == 'POST':
        
        if_success = create_database_with_request(request)

        if if_success:
            static_users, regular_users, bandwidth, _ = parse_database(DATABASE) # get default users and bandwidth
            print("static_users: ", static_users, "regular_users: ", regular_users, "bandwidth: ", bandwidth)

            implement_configuration(SWITCH_ID, static_users, regular_users, bandwidth)

            return DATABASE, status.HTTP_201_CREATED
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST
    
    elif request.method == 'DELETE':

        if_success = delete_database_with_request(request)

        if if_success:
            return DATABASE, status.HTTP_205_RESET_CONTENT
        else:
            return DATABASE, status.HTTP_400_BAD_REQUEST
    else:
        # request.method == 'GET'
        return DATABASE, status.HTTP_200_OK


def reset_matrix(num_user):

    # initialize meter matrix
    meter_matrix1 = list(range(1, num_user + 1))  ## XXX meter id starts from 1 (not 0) XXX
    meter_matrix2 = list(range(RANGE + 1, RANGE + num_user + 1))  # add RANGE to distinct

    # initialize flow matrix
    flow_matrix1 = [] # init as list of user's flow
    flow_matrix2 = [] # init as list of user's flow
    static_flow1 = [] # init as list of user's flow
    static_flow2 = [] # init as list of user's flow

    for j in range(num_user): # first one not used, increased everytime creating flows
        start_flow_id = j * MAX_FLOW + MAX_FLOW
        static_flow1.append([start_flow_id])  # starts id
        static_flow2.append([RANGE + start_flow_id])  # starts id

    for j in range(num_user): # first one not used, increased everytime creating flows
        # XXX the last MAX_FLOW means we reserve [0, MAX_FLOW] for specific flows
        # flow_matrix[i][j] = [i * num_bs * MAX_FLOW + j * MAX_FLOW + MAX_FLOW]  
        start_flow_id = j * MAX_FLOW + MAX_FLOW
        flow_matrix1.append([2*RANGE + start_flow_id])  # starts id
        flow_matrix2.append([3*RANGE + start_flow_id])  # add RANGE to distinct

    return meter_matrix1, meter_matrix2, flow_matrix1, flow_matrix2, static_flow1, static_flow2

def implement_configuration(switch_id, static_users, regular_users, bandwidth, table_id=0):
    global PRIORITY, INDICATOR

    start_time = time.time()
    # initial matrix 
    meter_matrix1, meter_matrix2, flow_matrix1, flow_matrix2, static_flow1, static_flow2 = reset_matrix(len(static_users)+len(regular_users)) # initialize these matrix

    ######### create dynamic path with bandwidth ########## TODO remove static user first
    if INDICATOR:
        static_flow = static_flow1
        flow_matrix = flow_matrix1
        meter_matrix = meter_matrix1
    else:
        static_flow = static_flow2
        flow_matrix = flow_matrix2
        meter_matrix = meter_matrix2

    ######### create static path ########## 
    for i in range(len(static_users)):
        idx = ORDERED_USERS.index(static_users[i])
        create_network_inverse(switch_id, static_users[i], static_flow[idx], -1, 1, 12, PRIORITY, table_id)  # for both bs1 and bs2

    # create new meters
    for i in range(len(regular_users)):
        add_meter(switch_id, bandwidth[i], meter_matrix[i]) # add the meter
        idx = ORDERED_USERS.index(regular_users[i]) # find the idx and thus find the corresponding flows and meters

        flow_matrix[idx] = create_network_inverse(switch_id, regular_users[i], flow_matrix[idx], meter_matrix[idx], 1, 12, PRIORITY, table_id) # XXX port hard code
        # TODO make sure to connect ethenet cable between port 5 and 7
        # flow_matrix[idx] = create_network_inverse(switch_id, regular_users[i], flow_matrix[idx], meter_matrix[idx], 7, 12, PRIORITY, table_id) # XXX port hard code

    if INDICATOR:  # XXX we HAVE TO remove them for each time, otherwise the meter overwrite will lead to switch unresponsive!
        clear_flow(switch_id, static_flow2)
        clear_flow(switch_id, flow_matrix2)
        clear_meter(switch_id, meter_matrix2)
    else:
        clear_flow(switch_id, static_flow1)
        clear_flow(switch_id, flow_matrix1)
        clear_meter(switch_id, meter_matrix1)
    
    print(time.time() - start_time)

    # update bandwidth
    PRIORITY = (PRIORITY + 1) % MAX_PRIORITY # increase priority so that the previous flows are not used

    INDICATOR = not INDICATOR # swap


##############################################################################################################################
##############################################################################################################################
##############################################################################################################################

#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Run this file using sudo (eg. sudo python BW_Limiter_api_v001.py)

# XXX ReadMe: static allocaton of flow ids: [1] for arp broadcast, [3,4] and [5,6] for const hosts(base stations), others start from MAXFLOW
# XXX ReadMe: flow matrix for both static and regular users are with total users numbers instead of individual numbers, easy to map

static_users, regular_users, bandwidth, const_hosts = parse_database(DATABASE) # get default users and bandwidth

############################ clear switch, init group and add broadcast arp flows ############################################
for _ in range(100):
    #clear all preliminary/default flows and meters on switch
    clear_all(SWITCH_ID)  # clear flows in the switch
    print('completed!')
    # create group for multi-casting on connected ports
    add_group(SWITCH_ID, PORT_LISTS) 

    add_arp_broadcast(SWITCH_ID, MIN_PRIORITY+1) # TODO fixme 1

    # create constant path for base station 1 and 2 toward core network # TODO fixme 2, 4
    for i in range(len(const_hosts)):
        create_network(SWITCH_ID, const_hosts[i], [MIN_PRIORITY+2*(i+1)], -1, PORT_LISTS[0], PORT_LISTS[1], MIN_PRIORITY)  

    ############################  main loop for REST api  ####################################################################
# for _ in range(100):
    implement_configuration(SWITCH_ID, static_users, regular_users, bandwidth)

    time.sleep(1)
    print('completed!')

hypervisor.run(port=7777)

print('completed!')
