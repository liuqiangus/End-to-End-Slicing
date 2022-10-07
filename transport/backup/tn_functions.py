import requests
import sys
import time
import numpy as np
import csv
import os

MAX_FLOW = 100
MAX_PRIORITY = 32768 - 1  # XXX fixed in this swtich
MIN_PRIORITY = 1  # XXX fixed in this swtich
RANGE = 1000 # RANGE FOR DISTINCT FLOWS AND METERS ID

headers = {
'Accept': "application/json",
'Content-Type': "application/json",
'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
}

def handle_response(response):
    if (response.status_code >= 200 and response.status_code <= 300):
        print('O', end=" ")
    else:
        print('X', end=" ")

def clear_all(switch_id):
    url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(switch_id)+"/"
    payload = ""
    response = requests.request("DELETE", url, data=payload, headers=headers)
    handle_response(response)

def clear_flow(switch_id, flow_id, table_id=0):
	if isinstance(flow_id, int): # if input is single flow id
		flow_id = [flow_id]
	
	for flow in flow_id:
		url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(switch_id)+"/table/"+str(table_id)+"/flow/"+str(flow)
		payload = ""
		response = requests.request("DELETE", url, data=payload, headers=headers)
		handle_response(response)

def clear_table(switch_id, table_id=0):
    url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(switch_id)+"/table/"+str(table_id)
    payload = ""
    response = requests.request("DELETE", url, data=payload, headers=headers)
    handle_response(response)

def clear_meter(switch_id, meter_id):
	if isinstance(meter_id, int): # if input is single flow id
		meter_id = [meter_id]
	
	for meter in meter_id:
		url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(switch_id)+"/meter/"+str(meter)
		payload = ""
		response = requests.request("DELETE", url, data=payload, headers=headers)
		handle_response(response)

def add_meter(switch_id, bandwidth, meter_id):
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:meter/'+str(meter_id)
	kbps=int(float(bandwidth)*1000)
	#xml code to add a meter
	
	payload = '{\
    "meter": {\
        "meter-id": "'+str(meter_id)+'",\
        "container-name": "mymeter",\
        "meter-band-headers": {\
            "meter-band-header": {\
                "band-id": "0",\
                "meter-band-types": { "flags": "ofpmbt-drop" },\
                "band-burst-size": "'+str(kbps)+'",\
                "drop-rate": "'+str(kbps)+'",\
                "drop-burst-size": "'+str(kbps)+'",\
                "band-rate": "'+str(kbps)+'"\
            }\
        },\
        "meter-name": "mymeter",\
        "flags": "meter-kbps"\
    }\
}'

	response = requests.request("PUT", url, data=payload, headers=headers)
	handle_response(response)

def query_stats(switch_id):
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)
	#xml code to add a meter
	
	response = requests.request("GET", url, data='', headers=headers)
	handle_response(response)


def add_arp_broadcast(switch_id, flow_id, priority=1, table_id=0, group_id=1):
	#the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:table/'+str(table_id)+'/flow/'+str(flow_id)

    payload = '{\
    "flow": {\
        "id": "'+str(flow_id)+'",\
        "hard-timeout": "0",\
        "idle-timeout": "0",\
        "match": {\
            "ethernet-match": {\
                "ethernet-type": { "type": "2054" }\
            }\
        },\
        "cookie": "'+str(flow_id+1)+'",\
        "instructions": {\
            "instruction": {\
                "order": "0",\
                "apply-actions": {\
                    "action": {\
                        "order": "0",\
                        "group-action": { "group-id": "'+str(group_id)+'" }\
                    }\
                }\
            }\
        },\
        "priority": "'+str(priority)+'",\
        "table_id": "'+str(table_id)+'"\
    }\
}'

    response = requests.request("PUT", url, data=payload, headers=headers)
    handle_response(response)

def add_flow_arp(switch_id, in_port, flow_id, table_id, out_port, priority=1):
	#the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:table/'+str(table_id)+'/flow/'+str(flow_id)

    payload = '{\
    "flow": {\
        "id": "'+str(flow_id)+'",\
        "hard-timeout": "0",\
        "idle-timeout": "0",\
        "match": {\
            "ethernet-match": {\
                "ethernet-type": { "type": "2054" }\
            },\
        "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'"\
        },\
        "cookie": "'+str(flow_id+1)+'",\
        "instructions": {\
            "instruction": {\
                "order": "0",\
                "apply-actions": {\
                    "action": {\
                        "order": "0",\
                        "output-action": { \
                          "max-length": "65535",\
                          "output-node-connector": "'+str(out_port)+'" \
                        }\
                    }\
                }\
            }\
        },\
        "priority": "'+str(priority)+'",\
        "table_id": "'+str(table_id)+'"\
    }\
}'

    response = requests.request("PUT", url, data=payload, headers=headers)
    handle_response(response)

def add_flow_arp_broadcast(switch_id, in_port, flow_id, table_id, group_id, priority=1):
	#the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:table/'+str(table_id)+'/flow/'+str(flow_id)

    payload = '{\
    "flow": {\
        "id": "'+str(flow_id)+'",\
        "hard-timeout": "0",\
        "idle-timeout": "0",\
        "match": {\
            "ethernet-match": {\
                "ethernet-type": { "type": "2054" }\
            },\
        "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'"\
        },\
        "cookie": "'+str(flow_id+1)+'",\
        "instructions": {\
            "instruction": {\
                "order": "0",\
                "apply-actions": {\
                    "action": {\
                        "order": "0",\
                        "group-action": { "group-id": "'+str(group_id)+'" }\
                    }\
                }\
            }\
        },\
        "priority": "'+str(priority)+'",\
        "table_id": "'+str(table_id)+'"\
    }\
}'

    response = requests.request("PUT", url, data=payload, headers=headers)
    handle_response(response)


def add_group(switch_id, port_lists, group_id=1):
	
	#the initial GET
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/group/'+str(group_id)

	buckets = ''

	for i, port in enumerate(port_lists):
		buckets += '{\
          "bucket-id": "'+str(i)+'",\
          "watch_group": "4294967295",\
          "weight": "1",\
          "action": {\
            "order": "0",\
            "output-action": {\
              "max-length": "0",\
              "output-node-connector": "'+str(port)+'"\
            }\
          },\
          "watch_port": "4294967295"\
        },'

	buckets = buckets[:-1] # remove the last one comma ","
	#add a flow entry with a meter
	payload = '{\
    "group": {\
    "group-id": "'+str(group_id)+'",\
    "group-type": "group-all",\
    "buckets": {\
      "bucket": [\
        ' + buckets + '\
      ]\
    }\
  }\
}'

	response = requests.request("PUT", url, data=payload, headers=headers)
	handle_response(response)

	return group_id

def add_flow_ipv4_with_meter(switch_id, in_port, out_port, user_addr, meter_id, flow_id, table_id, if_src, priority):	
	if if_src:
		ip_part = "source"
	else:
		ip_part = "destination"

	#the initial GET
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:table/'+str(table_id)+'/flow/'+str(flow_id)

	if meter_id > 0:
		#add a flow entry with a meter
		payload = '{\
    "flow": {\
        "id": "'+str(flow_id)+'",\
        "hard-timeout": "0",\
        "idle-timeout": "0",\
        "match": {\
            "ethernet-match": {\
            "ethernet-type": { "type": "2048" }\
        },\
        "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'",\
        "ipv4-'+str(ip_part)+'": "'+str(user_addr)+'/32"\
    },\
    "cookie": "'+str(flow_id+1)+'",\
    "instructions": {\
        "instruction": [\
        {\
            "order": "0",\
            "meter": { "meter-id": "'+str(meter_id)+'" }\
        },\
        {\
            "order": "1",\
            "apply-actions": {\
                "action": {\
                    "order": "0",\
                    "output-action": {\
                        "max-length": "65535",\
                        "output-node-connector": "'+str(out_port)+'"\
                    }\
                }\
            }\
        }\
        ]\
    },\
    "priority": "'+str(priority)+'",\
    "table_id": "'+str(table_id)+'"\
    }\
}'
	else:
		#add a flow entry without a meter
		payload = '{\
    "flow": {\
        "id": "'+str(flow_id)+'",\
        "hard-timeout": "0",\
        "idle-timeout": "0",\
        "match": {\
            "ethernet-match": {\
            "ethernet-type": { "type": "2048" }\
        },\
        "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'",\
        "ipv4-'+str(ip_part)+'": "'+str(user_addr)+'/32"\
    },\
    "cookie": "'+str(flow_id+1)+'",\
    "instructions": {\
        "instruction": [\
        {\
            "order": "1",\
            "apply-actions": {\
                "action": {\
                    "order": "0",\
                    "output-action": {\
                        "max-length": "65535",\
                        "output-node-connector": "'+str(out_port)+'"\
                    }\
                }\
            }\
        }\
        ]\
    },\
    "priority": "'+str(priority)+'",\
    "table_id": "'+str(table_id)+'"\
    }\
}'
	response = requests.request("PUT", url, data=payload, headers=headers)
	handle_response(response)


def add_flow_ipv4_with_meter_detail(switch_id, in_port, out_port, user_addr, flow_id, table_id, if_src, priority):	

	#the initial GET
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(switch_id)+'/flow-node-inventory:table/'+str(table_id)+'/flow/'+str(flow_id)

	if if_src:
		#add a flow entry with specific det addr
		payload = '{\
    "flow": {\
    "id": "'+str(flow_id)+'",\
    "hard-timeout": "0",\
    "idle-timeout": "0",\
    "match": {\
      "ethernet-match": {\
        "ethernet-type": { "type": "2048" }\
      },\
      "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'",\
      "ipv4-source": "'+str(user_addr)+'/32"\
    },\
    "cookie": "'+str(flow_id+1)+'",\
    "instructions": {\
      "instruction": {\
        "order": "1",\
        "apply-actions": {\
          "action": {\
            "order": "0",\
            "output-action": {\
              "max-length": "65535",\
              "output-node-connector": "'+str(out_port)+'"\
            }\
          }\
        }\
      }\
    },\
    "priority": "'+str(priority)+'",\
    "table_id": "'+str(table_id)+'"\
  }\
}'
	else:
		#add a flow entry without specific det addr
		payload = '{\
    "flow": {\
    "id": "'+str(flow_id)+'",\
    "hard-timeout": "0",\
    "idle-timeout": "0",\
    "match": {\
      "ethernet-match": {\
        "ethernet-type": { "type": "2048" }\
      },\
      "in-port": "openflow:'+str(switch_id)+':'+str(in_port)+'",\
      "ipv4-destination": "'+str(user_addr)+'/32",\
    },\
    "cookie": "'+str(flow_id+1)+'",\
    "instructions": {\
      "instruction": {\
        "order": "1",\
        "apply-actions": {\
          "action": {\
            "order": "0",\
            "output-action": {\
              "max-length": "65535",\
              "output-node-connector": "'+str(out_port)+'"\
            }\
          }\
        }\
      }\
    },\
    "priority": "'+str(priority)+'",\
    "table_id": "'+str(table_id)+'"\
  }\
}'
	response = requests.request("PUT", url, data=payload, headers=headers)
	handle_response(response)


def create_network(switch_id, user_addr, flow_list, meter_id, in_port, out_port, priority=1, table_id=0):

  flow_id = flow_list[-1] + 1 # increase one
  flow_list.append(flow_id)
  add_flow_ipv4_with_meter(switch_id, in_port, out_port, user_addr, meter_id, flow_id, table_id, True, priority)

  flow_id = flow_list[-1] + 1 # increase one
  flow_list.append(flow_id)
  add_flow_ipv4_with_meter(switch_id, out_port, in_port, user_addr, meter_id, flow_id, table_id, False, priority)

  return flow_list

def create_network_inverse(switch_id, user_addr, flow_list, meter_id, in_port, out_port, priority=1, table_id=0):

  flow_id = flow_list[-1] + 1 # increase one
  flow_list.append(flow_id)
  add_flow_ipv4_with_meter(switch_id, in_port, out_port, user_addr, meter_id, flow_id, table_id, False, priority)

  flow_id = flow_list[-1] + 1 # increase one
  flow_list.append(flow_id)
  add_flow_ipv4_with_meter(switch_id, out_port, in_port, user_addr, meter_id, flow_id, table_id, True, priority)

  return flow_list

# def create_network_detail(switch_id, users, table_id, flow_list, in_port, out_port, priority=MAX_PRIORITY):

# 	if not isinstance(users, list):
# 		users = [users]
    
# 	for i in range(len(users)):
# 		flow_id = flow_list[-1] + 1 # increase one
# 		flow_list.append(flow_id)
# 		add_flow_ipv4_with_meter_detail(switch_id, in_port, out_port, users[i], flow_list[0], table_id, True, priority)

# 		flow_id = flow_list[-1] + 1 # increase one
# 		flow_list.append(flow_id)
# 		add_flow_ipv4_with_meter_detail(switch_id, out_port, in_port, users[i], flow_list[1], table_id, False, priority)