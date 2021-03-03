# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
from socket import *

# Initialise the log file.
# logging.basicConfig(filename='Receiver1.logs',
#                     filemode='w',
#                     level=logging.INFO)

# Initialise argparser.
parser = argparse.ArgumentParser()
parser.add_argument('Port', type=int)
parser.add_argument('FileName', type=str)

# Read arguments.
args = parser.parse_args()
serverPort = args.Port
fileName = args.FileName
# logging.info("Arguments parsed.")

# Create server socket.
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))
# logging.info("Server initialised.")

# The received chunks will be saved in a dictionary.
chunks_dict = dict()
max_packet_number = -1
while(True):
    message, clientAddress = serverSocket.recvfrom(1027)

    packet_nr = int.from_bytes(message[0:2], 'big')
    flag = int.from_bytes(message[2:3], 'big')
    chunk = message[3:]

    # logging.info("Packet " + str(packet_nr) + " received.")
    if flag == 1:
        # Last packet detected; we can extract the max nr of packets from here.
        # This is not a guarantee that all the packets have been received (we're using UDP).
        max_packet_number = packet_nr
        # logging.info("Last sent packet received.")
    
    chunks_dict[packet_nr] = chunk

    if len(chunks_dict) == max_packet_number+1:
        # logging.info("All packets have been received.")
        serverSocket.close()
        break
    
# logging.info("Reconstructing file.")
with open(fileName, 'wb') as f:
    for ii in range(max_packet_number+1):
        f.write(chunks_dict[ii])
# logging.info("File saved.")
