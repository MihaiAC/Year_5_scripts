# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
import time
from socket import *
from typing import List, Dict, Tuple

# Initialise the log file.
logging.basicConfig(filename='Sender3.logs',
                    filemode='w',
                    level=logging.INFO)

# TODO: Need a variable for timeout for last message.
# TODO: Perhaps need to set a max number of wait cycles.
max_resends = 3
total_time = 0
total_bytes_sent = 0

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
logging.info("Arguments parsed.")

# We can send a maximum number of 2**16 packets (2 bytes).
# Each packet can transmit a maximum of 1024 bytes.
# Therefore, we can only transmit files of size <= 2**26 bytes.
if os.path.getsize(fileName) > 2**26:
    logging.info("File too large; script finished.")
    sys.exit("File too large.")

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

logging.info("Started sending packets.")
file_dict, max_packet_nr = read_whole_file(fileName)
max_packet_nr -= 1

print(max_packet_nr)
print(len(file_dict))

base_nr = 0
next_packet_nr = 0
while(True):
    # Send packets until the window is full.
    # Philosophical question: when is the window full? is it ever truly full?
    prev_next_packet_nr = next_packet_nr
    for ii in range(prev_next_packet_nr, min(max_packet_nr+1, base_nr+window_size)):
        flag = 1 if ii == max_packet_nr else 0
        message = ii.to_bytes(2, 'big') + flag.to_bytes(1, 'big') + file_dict[ii]
        clientSocket.sendto(message, (remoteHost, port))
        
        if ii == prev_next_packet_nr:
            clientSocket.settimeout(timeout/1000)

        logging.info("Sent packet " + str(ii))
        next_packet_nr += 1

    try:
        # We need to check that the seq number in the ACK corresponds to what
        # we were expecting (can receive ACKs for past resent packets, which were
        # resent too fast).
        while(True):
            ack_response, server_address = clientSocket.recvfrom(2)
            response_packet_number = int.from_bytes(ack_response, 'big')
            base_nr = response_packet_number + 1

            if base_nr == next_packet_nr: 
                break
            else:
                # receive_time = time.time()
                # total_time += receive_time - send_time
                clientSocket.settimeout(timeout/1000)

    except error:
        # Need to resend all packets starting from base.
        # logging.info("Packet " + str(packet_nr) + " needs to be resent.")

        # TODO: not sure if special treatment is needed for the last packet.
        # if flag == 1 and resends == max_resends:
        #     break
        # else:
        #     pass

        next_packet_nr = base_nr

    if base_nr == max_packet_nr+1:
        break

# print(str(total_bytes_sent/(1000*total_time)))
# How tf is total_time calculated here?
clientSocket.close()
logging.info("Finished sending all the packets.")
    