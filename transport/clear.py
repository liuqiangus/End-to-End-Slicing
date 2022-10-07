import time, os, sys, csv
import threading, socket, ctypes, requests
import numpy as np

from tn_functions import clear_all


#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Run this file using sudo (eg. sudo python BW_Limiter_api_v001.py)

#contains an array of the ruckus switch openflow id #'s'
switch_id = 211952888644863 # XXX find the correct switch id XXX

#  # my sdn switch

#clear all preliminary/default flows and meters on switch
clear_all(switch_id)  # clear flows in the switch
