# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
import time
import numpy as np
import math
from socket import *
from typing import List, Dict, Tuple

# Initialise the log file.
# logging.basicConfig(filename='Sender4.logs',
#                     filemode='w',
#                     level=logging.INFO)

max_resends = 3

# Initialise argparser.
parser = argparse.ArgumentParser()
parser.add_argument('RemoteHost', type=str)
parser.add_argument('Port', type=int)
parser.add_argument('FileName', type=str)
parser.add_argument('RetryTimeout', type=int)
parser.add_argument('WindowSize', type=int)

# Read arguments.
args = parser.parse_args()
remoteHost = args.RemoteHost
port = args.Port
fileName = args.FileName
timeout = args.RetryTimeout
window_size = args.WindowSize
# logging.info("Arguments parsed.")

timeout_seconds = timeout/1000

# We can send a maximum number of 2**16 packets (2 bytes).
# Each packet can transmit a maximum of 1024 bytes.
# Therefore, we can only transmit files of size <= 2**26 bytes.
if os.path.getsize(fileName) > 2**26:
    # logging.info("File too large; script finished.")
    sys.exit("File too large.")

# Read the file into 1024-byte chunks, save those in a dictionary and return it.
def read_whole_file(fileName:str) -> Tuple[Dict[int, bytes], int]:
    file_dict = dict()
    chunk_nr = 0
    with open(fileName, 'rb') as f:
        while(True):
            chunk = f.read(1024)
            if(len(chunk) == 0):
                break
            else:
                file_dict[chunk_nr] = chunk
                chunk_nr += 1
    return (file_dict, chunk_nr)

# Open up a client socket.
clientSocket = socket(AF_INET, SOCK_DGRAM)

# Make socket non-blocking.
clientSocket.settimeout(0)

# logging.info("Started sending packets.")
file_dict, max_packet_nr = read_whole_file(fileName)
max_packet_nr -= 1

base_nr = 0
transmission_start_time = time.time()

# ack_packet[x] = 1 if we received the ACK for packet x.
ack_packet = np.zeros((max_packet_nr+2, ))

# Dictionary of "timers".
packet_send_time = dict()

while(True):
    # Send all the unacked packets from the window.
    for ii in range(base_nr, min(max_packet_nr+1, base_nr+window_size)):
        # We send only unacked packets from the window.
        if not ack_packet[ii]:
            # Check timer for this packet. 
            # If it's expired, and the packet is unacknowledged send it.
            # If the packet doesn't have a timer, it means that it was never sent, so send it.
            if ii in packet_send_time and time.time()-packet_send_time[ii] < timeout_seconds:
                continue

            flag = 1 if ii == max_packet_nr else 0
            message = ii.to_bytes(2, 'big') + flag.to_bytes(1, 'big') + file_dict[ii]
            
            packet_send_time[ii] = time.time()
            clientSocket.sendto(message, (remoteHost, port))
            # logging.info("Sent packet " + str(ii))
         
    # Repeat this loop until either the timeout passes or we've repeated it for window_size times.
    # Or all packages in current windows have been received?

    # Timer might interfere with packets' own timer.
    repeats = window_size

    # Try reading window_size# of packets from the socket.
    while(repeats > 0):
        repeats -= 1
        try:
            ack_response, server_address = clientSocket.recvfrom(2)
            ack_packet_number = int.from_bytes(ack_response, 'big')
            # logging.info("Received ACK for packet " + str(ack_packet_number))
            ack_packet[ack_packet_number] = 1

        except error:
            continue
    
    # Update base number.
    old_base_nr = base_nr
    for ii in range(old_base_nr, min(max_packet_nr+1, base_nr+window_size)):
        if ack_packet[ii]:
            base_nr = ii+1
        else:
            break

    # ack_packet[max_packet_nr+1] is essentially a signal from the receiver to the sender
    # that all the packets have been received successfully.
    if base_nr == max_packet_nr+1 or ack_packet[max_packet_nr+1]:
        break

transmission_end_time = time.time()
total_transmission_time = transmission_end_time - transmission_start_time
file_size_in_bytes = os.path.getsize(fileName)
print(str(file_size_in_bytes/(1000*total_transmission_time)))
clientSocket.close()
# logging.info("Finished sending all the packets.")
    