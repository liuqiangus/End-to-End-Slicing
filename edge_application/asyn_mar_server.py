
import socket, time, sys, struct, os
import cv2, pickle, threading
import numpy as np
from flask import request, url_for
from flask_api import FlaskAPI, status, exceptions
from os import listdir
from os.path import isfile, join
from queue import Queue

HOST = '0.0.0.0'
USER_PORT = 9001
REST_PORT = USER_PORT + 1000

SIZE = 100 # number of comparing images
SOCKET_TIME_OUT = 10
INFOS = [1] # ms rtt
FOLDER = 'images/'
CWD = os.getcwd()
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
    frame = cv2.imdecode(imgdata, 1)

    return frame, id, buffers


def process(feature_extractor, matcher, image, database):

    latent = feature_extractor.inference(image)    
    obj_id = sub_process_matching(latent, database, matcher)

    return obj_id


class ORB:
    def __init__(self,):
        # Initiate ORB detector
        self.orb = cv2.ORB_create()
        # the default edgethreshold is 31, cannot detect keypoints
        # which is not suitable for small cropped image
        # reduce this value can apply to small image

    def inference(self, img):
        # find the keypoints with ORB
        kp = self.orb.detect(img, None)
        # compute the descriptors with ORB
        kp, des = self.orb.compute(img, kp)
        
        if des is None:
            # if no feature detected, then randomly generated 100 features.
            des = np.random.randint(0, 100, (100, 32), dtype=np.uint8)

        des = des[:100] # max number of features

        return des


def sub_process_matching(features, database, matcher):
    # given an object (loc, latent), find the corresponding object in global_database
    # the geo-distance should be smaller than NEARBY_DIST, and then find the minimum latent one
    # if not found, then report a new object detected.
    obj_id, min_aug_dist = 0, 1e9

    for key, latent in database.items():
        # where latent vector could be just a vector or a multi-vector due to orb detection            
        matches = matcher.match(latent, features) # store the latent dist
        avg_distance = np.mean([match.distance for match in matches])
            
        if avg_distance <= min_aug_dist: # if geo loc is nearby and aug-distance is smaller
            min_aug_dist = avg_distance
            obj_id = key

    return obj_id


def start_rest_api():
    server.run(host=HOST,port=REST_PORT)
    print('completed!')


def service_thread(user,):
    id, client, img_queue = user

    feature_extractor = ORB()
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    while True:
        try: # try to get image from image queue

            recv_time, frame_id, frame = img_queue.get() #  by default block=True

            start_time = time.time()

            match_id = process(feature_extractor, matcher, frame, database) # process the img

            result_str = str(match_id) + '\n'  # prepare data

            client.sendall(result_str.encode()) # send back to client

            encode_recv_id = (str(frame_id)+'\n').encode() # the size of first packet

            client.sendall(encode_recv_id) # send packet id recv before

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
    if len(sys.argv) == 1:
        max_img_numbers = 100
    elif len(sys.argv) == 2:
        max_img_numbers = int(sys.argv[1])
    else:
        raise ValueError

    # start rest api server
    t1 = threading.Thread(target = start_rest_api)
    t1.setDaemon(True)
    t1.start()

    # bind to port to accept client
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((HOST,USER_PORT))
    s.listen(1000)

    # global_database = {}
    # # get all images
    # images = [cv2.imread(FOLDER+f) for f in listdir(FOLDER) if isfile(join(FOLDER, f))]

    # # save to global images
    # for i, img in enumerate(images):
    #     latent = feature_extractor.inference(img)
    #     global_database[str(i)] = latent

    # with open('global_database.pkl', 'wb') as handler:
    #     pickle.dump(global_database, handler)
    #### handle different folders #####

    try:
        with open(CWD+'/offloading_servers/global_database.pkl', 'rb') as handler:
            global_database = pickle.load(handler)
    except: pass 
    try:
        with open('global_database.pkl', 'rb') as handler:
            global_database = pickle.load(handler)
    except: pass 

    database = {}
    for key, val in global_database.items():
        database[key] = val # get the value
        if len(database)>=max_img_numbers: break

    print('database length is ', len(database)) # if no global_database loaded, then report error

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
            
        


            