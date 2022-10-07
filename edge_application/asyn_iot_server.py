
import socket, time, sys, struct, os
import pickle, threading
import numpy as np
from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions
from os import listdir
from os.path import isfile, join
from queue import Queue

HOST = '0.0.0.0'
USER_PORT = 9003
REST_PORT = USER_PORT + 1000

PKT_SIZE = 1000 # size of pkt in Bytes
SOCKET_TIME_OUT = 10
INFOS = [1]
TRAFFIC = 1.0

USERS = {}  # store the user id, socket, queue

server = FlaskAPI(__name__)

@server.route("/", methods=['GET', 'POST', 'PUT'])
def function():
    global INFOS, TRAFFIC
    if request.method in ['POST', 'PUT']:
        traffic = str(request.data.get('traffic', ''))
        try:
            TRAFFIC = float(traffic)
            print("traffic: ", TRAFFIC)
        except: 
            pass

        perf = str(request.data.get('perf', ''))
        try:
            INFOS.append(float(perf))
            print("perf: ", float(perf))
        except: 
            pass
        
        return str(TRAFFIC), status.HTTP_202_ACCEPTED
    else:
        useful_len = int(len(INFOS)*0.8) # last 50%
        avg_data = int(100*np.mean(INFOS[useful_len:]))/100 # get average 
        INFOS = [INFOS[-1]] # reset the data
        # reset queue of all users
        for key, user in USERS.items():
            id, _, the_queue = user
            with the_queue.mutex: the_queue.queue.clear() # clear all
            print("clear queue for user: ", id, the_queue.qsize())

        return str(avg_data), status.HTTP_200_OK


def recv_image_from_socket(client, buffers):
    start_time = time.time() # time when recv starts
    # print("start buffers len: ", len(buffers))
    
    while len(buffers) < 8:
        try:
            buf = client.recv(1024)
        except:
            return False, 0, b''
        buffers += buf
        # if recv too long, then consider this user is disconnected
        if time.time() - start_time >= SOCKET_TIME_OUT:
            return False, 0, b''
        
    img_size_byte_pkt = buffers[:4] # here buffer could larger than 4 len
    img_id_byte_pkt = buffers[4:8] # here buffer could larger than 4 len
    buffers = buffers[8:] # here buffer could larger than 4 len

    size, = struct.unpack('!i', img_size_byte_pkt)
    id, = struct.unpack('!i', img_id_byte_pkt)
    # print("packet to be recvd: ", size)
    # print("middle remains len: ", len(buffers))

    while len(buffers) < size:
        try:
            buf = client.recv(1024)
        except:
            return False, 0, b''
        buffers += buf
        # if recv too long, then consider this user is disconnected
        if time.time() - start_time >= SOCKET_TIME_OUT:
            return False, 0, b''

    image_data = buffers[:size]
    buffers = buffers[size:]

    # print("late remains len: ", len(buffers))
    imgdata = np.frombuffer(image_data, dtype='uint8')
    frame = imgdata

    return frame, id, buffers


def start_rest_api():
    server.run(host=HOST,port=REST_PORT)
    print('completed!')


def service_thread(user,):
    id, client, img_queue = user

    while True:
        try: # try to get image from image queue
            
            recv_time, frame_id, recv_data = img_queue.get() #  by default block=True

            start_time = time.time()

            rgb = np.random.randint(0, 255, 3)
            
            real_data = str(rgb[0]) + ',' + str(rgb[1]) + ',' + str(rgb[2]) + ','
            concat_times = int(PKT_SIZE / len(real_data.encode()))
            send_data = ''
            for _ in range(concat_times): send_data += real_data
            
            frame_id_str = str(frame_id) + '\n'
            client.sendall(frame_id_str.encode()) # send back to client

            send_data_str = send_data + '\n' # \n as end to reminder readline in android app
            client.sendall(send_data_str.encode()) # send back to client

            send_time = int(1000*(time.time() - start_time))/1000
            if send_time > 1: print("process time (s): ", send_time, flush=True)

        except: # otherwise pass
            pass


def user_thread(user,):
    global USERS
    id, client, img_queue = user
    
    X = threading.Thread(target = service_thread, args=(user,))
    X.setDaemon(True)
    X.start()

    buffers = b''
    # if client connected, keeping processing its data
    while True:
        frame, frame_id, buffers = recv_image_from_socket(client, buffers) # receive from client
        
        if frame is False:
            USERS.pop(id, None) # remove the user
            print("droped client id: ", id)
            break
        
        recv_time = time.time()
        if img_queue.full(): img_queue.get() # if the queue is full, pop out the first one
        img_queue.put((recv_time, frame_id, frame)) # put into image queue and recv time stamp
        # print('recv id', frame_id, flush=True)

    client.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        PKT_SIZE = int(sys.argv[1])
    elif len(sys.argv) > 2:
        raise ValueError

    # start rest api server
    t1 = threading.Thread(target = start_rest_api)
    t1.setDaemon(True)
    t1.start()

    # bind to port to accept client
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((HOST,USER_PORT))
    s.listen(1000)

    idx = 0
    # main loop for all incoming client
    while True:
        print("waiting for client connection...")
        client_sock, addr = s.accept()  # accept client
        user_id = str(idx)
        user = (user_id, client_sock, Queue(1000))
        USERS[user_id] = user
        print ("new user socket id: ", user_id)
        idx += 1

        X = threading.Thread(target = user_thread, args=(user,))
        X.setDaemon(True)
        X.start()
            
        


            