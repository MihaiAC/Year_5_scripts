# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
from socket import *
from typing import Dict

resend_last_packet_n_times = 15

# logging.basicConfig(filename='Receiver4.logs',
#                     filemode='w',
#                     level=logging.INFO)

# Initialise argparser.
parser = argparse.ArgumentParser()
parser.add_argument('Port', type=int)
parser.add_argument('FileName', type=str)
parser.add_argument('WindowSize', type=int)

# Read arguments.
args = parser.parse_args()
serverPort = args.Port
fileName = args.FileName
window_size = args.WindowSize
# logging.info("Arguments parsed.")

# Create server socket.
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))
# logging.info("Server initialised.")

# The received chunks will be saved in a dictionary.
chunks_dict = dict()
rcv_base = 0
max_packet_nr = -1

while(True):
    message, clientAddress = serverSocket.recvfrom(1027)

    packet_nr = int.from_bytes(message[0:2], 'big')
    flag = int.from_bytes(message[2:3], 'big')
    chunk = message[3:]
    
    # Need to take special care for packets in last window.
    # SR is most dangerous for sender never ending.
    # Can send an ack for max_packet + 1 when all packets have been received.
    # Aka a contract between sender and receiver.
    # Can this never end?

    # logging.info("Packet " + str(packet_nr) + " received.")

    if packet_nr >= rcv_base-window_size and packet_nr <= rcv_base+window_size-1:
        # Resend packet.
        # logging.info("Sent ACK for packet: " + str(packet_nr) + ".")
        serverSocket.sendto(packet_nr.to_bytes(2, 'big'), clientAddress)
        chunks_dict[packet_nr] = chunk
    
    while rcv_base in chunks_dict:
        rcv_base += 1
    
    if flag == 1:
        max_packet_nr = packet_nr
    
    # If all packages have been received, send a few ACKs for max_packet_nr+1.
    # For the sender, this signal means that all packets have been received.
    if len(chunks_dict) == max_packet_nr+1:
        # logging.info("Sending termination ACKs.")
        max_packet_nr += 1
        for ii in range(resend_last_packet_n_times):
            serverSocket.sendto(max_packet_nr.to_bytes(2, 'big'), clientAddress)
        break
    
# logging.info("Reconstructing file.")
with open(fileName, 'wb') as f:
    for ii in range(max_packet_nr):
        f.write(chunks_dict[ii])
# logging.info("File saved.")
