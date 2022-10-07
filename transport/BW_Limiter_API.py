import requests
import time
import os
import flow_v005 as flow
import numpy as np
import sys
import ctypes
import threading
import socket
# import connector
import csv

#v13
switch = [106225813884292]

b1_u=[
'12.1.1.2',
'10.0.0.100'
]

b2_u=[]

nou=len(b2_u)+len(b1_u)

d_bw=[1, 100]

num_t=2

max_num_meters=int(1024/nou)
m_l = np.zeros((num_t,nou,len(switch), max_num_meters)) 

f_l = np.empty([num_t,nou,len(switch),int(512/nou),7], dtype=object) 

for n in range(0,len(switch)):
  flow.clear(switch[n])

for e in range(0,num_t):
  for u in range(0,nou): 
    for s in range(0,len(switch)): 
      m_l[e][u][s][0] = flow.add_meter(switch[s],d_bw[u])

f_num = np.zeros((2,len(switch)))

# top_num=0
# f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])

flow.add_flow_arp_with_meter(switch[0], 12, 1, 1, 0, 10, 0, 1)
flow.add_flow_arp_with_meter(switch[0], 1, 12, 1, 0, 11, 0, 1)

for u in range(0,len(b1_u)):
		temp = flow.add_flow_with_meter(switch[0],12,1,b1_u[u],m_l[0][u][0][0],0)
		temp = flow.add_flow_with_meter(switch[0],1,12,b1_u[u],m_l[0][u][0][0],1)
