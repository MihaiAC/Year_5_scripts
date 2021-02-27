# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
import time
from functools import partial
from socket import *
from typing import List, Dict, Tuple

# Initialise the log file.
# logging.basicConfig(filename='Sender3.logs',
#                     filemode='w',
#                     level=logging.INFO)

# Maximum resends for the last packet.
last_pack_max_resends = 15

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
timeout_ms = args.RetryTimeout
timeout_s = timeout_ms/1000
window_size = args.WindowSize
# logging.info("Arguments parsed.")

# We can send a maximum number of 2**16 packets (2 bytes).
# Each packet can transmit a maximum of 1024 bytes.
# Therefore, we can only transmit files of size <= 2**26 bytes.
if os.path.getsize(fileName) > 2**26:
    # logging.info("File too large; script finished.")
    sys.exit("File too large.")

def read_whole_file(fileName:str) -> Tuple[Dict[int, bytes], int]:
    file_dict = dict()
    chunk_nr = 1
    with open(fileName, 'rb') as f:
        while(True):
            chunk = f.read(1024)
            if(len(chunk) == 0):
                break
            else:
                file_dict[chunk_nr] = chunk
                chunk_nr += 1
    return (file_dict, chunk_nr-1)

def timer_timeout(init_time:float, timeout_s:float) -> bool:
    return init_time != 0 and ((time.time() - init_time) > (timeout_s))

# Open up a client socket.
clientSocket = socket(AF_INET, SOCK_DGRAM)
# Make client socket non-blocking.
clientSocket.settimeout(0)

# logging.info("Started sending packets.")
file_dict, max_packet_nr = read_whole_file(fileName)
# Packet numbers will start from 1 in this case.

# base_nr corresponds to "base" from the book GBN algorithm.
base_nr = 1
nextseqnum = 1

init_time = time.time()
transmission_start_time = time.time()

clamp = partial(min, max_packet_nr+1)

# "rdt_send" is called only when there is free space in the queue.
while(True):
    # If the timer has timeout, re-send all the packets from base to nextseqnum-1.
    if timer_timeout(init_time, timeout_s):
        # Restart timer.
        init_time = time.time()
        for ii in range(base_nr, clamp(nextseqnum)):
            flag = 1 if ii == max_packet_nr else 0
            message = ii.to_bytes(2, 'big') + flag.to_bytes(1, 'big') + file_dict[ii]
            clientSocket.sendto(message, (remoteHost, port))
            # logging.info("Re-sent packet " + str(ii))

    # Next, send packets until the window is full.
    # Packets that can be sent are in the range [nextseqnum, base+window_size-1].
    aux_nextseqnum = nextseqnum
    for ii in range(aux_nextseqnum, clamp(base_nr+window_size)):
        flag = 1 if ii == max_packet_nr else 0
        message = ii.to_bytes(2, 'big') + flag.to_bytes(1, 'big') + file_dict[ii]
        clientSocket.sendto(message, (remoteHost, port))
        
        # If base number is equal to nextseqnum, reset the timer.
        if base_nr == nextseqnum:
            init_time = time.time()

        # logging.info("Sent packet " + str(ii))
        nextseqnum += 1

    # Current solution: 
    # Try at least once; if no packets have been received, we keep trying until 
    # the timeout occurs.

    # If a packet has been received, read until either the timer expires
    # or the base number changes (why? if the base number has not moved,
    # we will not send any new packets anyway; we can only resend packets
    # after timeout occurs).
    pkt_received = 0
    while True:
        try:
            ack_response, server_address = clientSocket.recvfrom(2)
            response_packet_number = int.from_bytes(ack_response, 'big')
            base_nr = response_packet_number + 1
            pkt_received = 1
            if base_nr == nextseqnum:
                # "Stop" the timer (all the packages in the current window have been sent).
                init_time = 0
            else:                
                # Reset the timer.
                init_time = time.time()
        except error:
            pass
        if pkt_received or timer_timeout(init_time, timeout_s):
            break
    
    # If all the packets have been sent OR the last packet has been send the max
    # number of times, end the program.
    if base_nr == max_packet_nr+1 or last_pack_max_resends == 0:
        break
    
    # If we're at the last packet, decrement the number of max resends for the last packet.
    if base_nr == max_packet_nr:
        last_pack_max_resends -= 1

transmission_end_time = time.time()
total_transmission_time = transmission_end_time - transmission_start_time
file_size_in_bytes = os.path.getsize(fileName)
print(str(file_size_in_bytes/(1000*total_transmission_time)))
clientSocket.close()
# logging.info("Finished sending all the packets.")
