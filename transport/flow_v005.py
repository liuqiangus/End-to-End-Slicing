import requests
import sys
import time
import numpy as np
import csv
import os

headers = {
'Accept': "application/xml",
'Content-Type': "application/xml",
'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
}


def clear(*args):

	url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(args[0])+"/"

	payload = ""
	response = requests.request("DELETE", url, data=payload, headers=headers)
	
	if ((response.status_code==200) or (response.status_code==404)):
		print('Switch '+str(args[0])+' was cleared\n')
	else:
		print('ERROR:Unable to clear Switch '+str(args[0])+'\n')

def add_meter(*args):
	
	meter_num=1

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(meter_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)

	while(response.status_code<>404):
		meter_num=meter_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(meter_num)
		response = requests.request("GET", url, data=payload, headers=headers)
	
	kbps=int(float(args[1])*1000)

	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<meter xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<meter-id>"+str(meter_num)+"</meter-id>\n\
\t<container-name>mymeter</container-name>\n\
\t<meter-name>mymeter</meter-name>\n\
\t<flags>meter-kbps</flags>\n\
\t<meter-band-headers>\n\
\t\t<meter-band-header>\n\
\t\t\t<band-id>0</band-id>\n\
\t\t\t<band-rate>"+str(kbps)+"</band-rate>\n\
\t\t\t<meter-band-types>\n\
\t\t\t\t<flags>ofpmbt-drop</flags>\n\
\t\t\t</meter-band-types>\n\
\t\t\t<band-burst-size>"+str(kbps)+"</band-burst-size>\n\
\t\t\t<drop-rate>"+str(kbps)+"</drop-rate>\n\
\t\t\t<drop-burst-size>"+str(kbps)+"</drop-burst-size>\n\
\t\t</meter-band-header>\n\
\t</meter-band-headers>\n\
</meter>"

	response = requests.request("PUT", url, data=payload, headers=headers)

	if (response.status_code==201):
		print('Meter '+str(meter_num)+' was added\n')
		return(meter_num)
	else:
		print(str(response.text)) #debuging code
		print('ERROR:Unable to add Meter '+str(meter_num)+'\n')
		return(99999)

def modify_meter(*args):

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(args[1])

	payload=''
	response = requests.request("DELETE", url, data=payload, headers=headers)

	kbps=int(float(args[2])*1000)
	print('kbps rate limit='+str(kbps)) #debuging code

	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<meter xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<meter-id>"+str(args[1])+"</meter-id>\n\
\t<container-name>mymeter</container-name>\n\
\t<meter-name>mymeter</meter-name>\n\
\t<flags>meter-kbps</flags>\n\
\t<meter-band-headers>\n\
\t\t<meter-band-header>\n\
\t\t\t<band-id>0</band-id>\n\
\t\t\t<band-rate>"+str(kbps)+"</band-rate>\n\
\t\t\t<meter-band-types>\n\
\t\t\t\t<flags>ofpmbt-drop</flags>\n\
\t\t\t</meter-band-types>\n\
\t\t\t<band-burst-size>100</band-burst-size>\n\
\t\t\t<drop-rate>"+str(kbps)+"</drop-rate>\n\
\t\t\t<drop-burst-size>1000</drop-burst-size>\n\
\t\t</meter-band-header>\n\
\t</meter-band-headers>\n\
</meter>"

	response = requests.request("PUT", url, data=payload, headers=headers)

	if ((response.status_code==201) or (response.status_code==200)):
		print('Meter '+str(args[1])+' was modified\n')
	else:
		print(str(response.text)) #debuging code
		print('ERROR:Unable to modify Meter '+str(args[1])+'\n')

def add_flow_with_meter(*args):

	flow_num=1

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)
	
	while(response.status_code<>404):
		flow_num=flow_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
		response = requests.request("GET", url, data=payload, headers=headers)
	ip_data=[]
	if(args[5]==1):
		ip_part="destination"
		ip_data.append(' ')
		ip_data.append(str(args[3]))
	else:
		ip_part="source"
		ip_data.append(str(args[3]))
		ip_data.append(' ')


	priority_part="1"

	flow_type=['ARP','IPv4']
	temp=np.zeros((int(len(flow_type))))
	# temp[0]=add_flow_arp_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
	temp[1]=add_flow_ipv4_with_meter(args[0],args[1],args[2],args[3],args[4],temp[0]+1,ip_part,int(priority_part))
	


def add_flow_arp_with_meter(*args):

	flow_num=int(args[5])

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)

	while(response.status_code<>404):
		flow_num=flow_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
		response = requests.request("GET", url, data=payload, headers=headers)

		
	# if(len(args[6])=='destination'):
	# 	prio_part=str(int(args[7])+1)
	# else:
	prio_part=str(args[7])
			

	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2054</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(prio_part))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"

	
	response = requests.request("PUT", url, data=payload, headers=headers)

	if ((response.status_code==200) or (response.status_code==201)):
		print('ARP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
		return(flow_num)
	else:
		print('ERROR:Unable to add arp flow entry to table 0 slot '+str(flow_num)+'.\n')
		return(0)

def add_flow_ipv4_with_meter(*args):
	
	flow_num=int(args[5])

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)

	while(response.status_code<>404):
		flow_num=flow_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
		response = requests.request("GET", url, data=payload, headers=headers)

	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
	
	response = requests.request("PUT", url, data=payload, headers=headers)

	if ((response.status_code==200) or (response.status_code==201)):
		print('IPv4 Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
		return(flow_num)
	else:
		print('ERROR:Unable to add ipv4 flow entry to table 0 slot '+str(flow_num)+'.\n')
		return(0)

def add_flow_tcp_with_meter(*args):

	flow_num=int(args[5])

	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)

	while(response.status_code<>404):
		flow_num=flow_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
		response = requests.request("GET", url, data=payload, headers=headers)
  
	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<ip-match>\n\
\t\t\t<ip-protocol>6</ip-protocol>\n\
\t\t</ip-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
	
	response = requests.request("PUT", url, data=payload, headers=headers)

	if ((response.status_code==200) or (response.status_code==201)):
		print('TCP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
		return(flow_num)
	else:
		print('ERROR:Unable to add tcp flow entry to table 0 slot '+str(flow_num)+'.\n')
		return(0)

def add_flow_icmp_with_meter(*args):
	flow_num=int(args[5])


	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
	payload = ""
	response = requests.request("GET", url, data=payload, headers=headers)

	while(response.status_code<>404):
		flow_num=flow_num+1
		url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
		response = requests.request("GET", url, data=payload, headers=headers)
  
	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<ip-match>\n\
\t\t\t<ip-protocol>1</ip-protocol>\n\
\t\t</ip-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
	
	response = requests.request("PUT", url, data=payload, headers=headers)

	if ((response.status_code==200) or (response.status_code==201)):
		print('ICMP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
		return(flow_num)
	else:
		print('ERROR:Unable to add icmp flow entry to table 0 slot '+str(flow_num)+'.\n')
		return(0)

def add_f_l(*args):
	entry_count=0
	p=0
	while((p<len(args[0][0][0])) and (entry_count<len(args[3]))):
		if ((args[0][args[1]][args[2]][p][0]==0) or (args[0][args[1]][args[2]][p][0]==None)):
			args[0][args[1]][args[2]][p] = args[3][entry_count]
			entry_count=entry_count+1
		p=p+1
	return(args[0])

def modify_f_l(*args):

	temp = args[0]	
	emp = np.empty([1,len(temp[0][0][0])], dtype=object)

	for u in range(0,len(temp)):
		for s in range(0,len(temp[0])):
			for f in range(0,len(temp[0][0])):
				if((temp[u][s][f][4]<>None) and (int(temp[u][s][f][4])<>0) and (temp[u][s][f][4]==int(args[1]))):
					temp[u][s][f]=emp

	return(temp)
	
	
def output_flow(*args):
	b1_u=args[0]
	b2_u=args[1]
	nou=args[2]
	switch=args[3]
	f_l=args[4]
	top_num=args[5]

	os.remove('flow_entries.csv')
	f1 = open('flow_entries.csv','w')
	f1.truncate()
	writer = csv.writer(f1)
	writer.writerow(['Topology #','Switch #','Flow #','Priority #','Protocol','Action','Meter #','Source Add.','Destination Add.'])
	b=[]
	b.extend(b1_u)
	b.extend(b2_u)
	for l in range(0,nou):
		for p in range(0,len(switch)):
			q=0
			while(q<len(f_l[0][0][0])):
				if(f_l[top_num][l][p][q][0]<>None):
					if(int(f_l[top_num][l][p][q][0])<>0):
						a=[]
						a.extend([str(top_num),p+1])
						a.extend(f_l[top_num][l][p][q])
						writer.writerow(a)
					else:
						break
				else:
					break
				q=q+1
	f1.close()

def create_topology(*args):
	b1_u = args[0]
	b2_u = args[1]
	f_l = args[2]
	switch = args[3]
	m_l = args[4]
	
	b_num = 1
	for u in range(0,len(b1_u)):
		temp = add_flow_with_meter(switch[0],12,1,b1_u[u],m_l[u][0][0],0,switch,b_num)
		temp = add_flow_with_meter(switch[0],1,12,b1_u[u],m_l[u][0][0],1,switch,b_num,99)

	print('SDN Network Setup Complete!\n\n')
	
	return(f_l)


