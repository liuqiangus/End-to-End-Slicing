
import socket, time, sys, struct, os
import pickle, threading
import numpy as np
from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions
from os import listdir
from os.path import isfile, join
from queue import Queue

HOST = '0.0.0.0'
USER_PORT = 9009
REST_PORT = USER_PORT + 1000

SOCKET_TIME_OUT = 10
INFOS = [1] # ms fps
TRAFFIC = 1.0

FRAMES = {} # store the extracted frames
USERS = {}  # store the user id, socket, queue

server = FlaskAPI(__name__)

@server.route("/", methods=['GET', 'POST', 'PUT'])
def function():
    global INFOS, TRAFFIC, USERS
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
        
        return str(TRAFFIC), status.HTTP_202_ACCEPTED # return traffic, directly to UE 
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
    
    while len(buffers) < 8: # TODO hardcode here
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
    
    frame = size # size of image

    return frame, id, buffers


def start_rest_api():
    server.run(host=HOST,port=REST_PORT)
    print('completed!')


def get_frames_from_video_file(path='test.mp4'):
    import cv2
    frames = {}
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
    cv_capture = cv2.VideoCapture(path)

    available, count = True, 0
    while (available):
        available, frame = cv_capture.read()
        if frame is None: break

        result, jpg_frame = cv2.imencode('.jpg', frame, encode_param)

        frames[str(count)] = jpg_frame.tobytes()

        print(count, end=" ")
        count += 1
    
    print("all frames extracted, len: ", len(frames))
    return frames

def service_thread(user,):
    global FRAMES 
    id, client, img_queue = user
    frame_id = 0

    # if client connected, keeping processing its data
    while True:
        time.sleep(1/TRAFFIC/30)
        frame_id += 1
        # _, frame_id, _ = img_queue.get() #  by default block=True, just for sending signal

        start_time = time.time()

        frame_bytes = FRAMES[str(frame_id % len(FRAMES))] # get the front one

        data_len_bytes = format(len(frame_bytes), '08d').encode() # fixed length TODO match the client side
        if len(frame_bytes) > 1e8: raise ValueError ("revised hardcore 08d!") # print("data len: ", data_len_str, flush=True)
        frame_id_bytes = format(frame_id, '08d').encode()         # fixed length TODO match the client side
        
        try:  ### send img data ###
            client.sendall(data_len_bytes + frame_id_bytes + frame_bytes) # bytes can conate 
        except:
            break # if send error, the client is down, break

        send_time = int(1000*(time.time() - start_time))/1000
        if send_time > 1: print("process time (s): ", send_time, flush=True)

    client.close()

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
    if len(sys.argv) == 1:
        video_path = 'test.mp4'
    elif len(sys.argv) == 2:
        video_path = sys.argv[1]
    else:
        raise ValueError

    # FRAMES = get_frames_from_video_file(video_path) # get all frames from given video path

    # with open('frames.pkl', 'wb') as handler:
    #     pickle.dump(FRAMES, handler)

    try:
        with open(os.getcwd()+'/offloading_servers/frames.pkl', 'rb') as handler:
            FRAMES = pickle.load(handler)
    except: 
        pass
    try:
        with open('frames.pkl', 'rb') as handler:
            FRAMES = pickle.load(handler)
    except: 
        pass

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
            
        


            