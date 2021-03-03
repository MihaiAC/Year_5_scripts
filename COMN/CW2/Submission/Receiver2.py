# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
from socket import *

# Mechanism for correct termination.
resend_last_packet_n_times = 15

# logging.basicConfig(filename='Receiver2.logs',
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
serverSocket.setsockopt(SOL_SOCKET, SO_SNDBUF, 16384)
serverSocket.setsockopt(SOL_SOCKET, SO_RCVBUF, 131072)
# logging.info("Server initialised.")

# The received chunks will be saved in a dictionary.
chunks_dict = dict()
nr_sent_packets = -1
while(True):
    message, clientAddress = serverSocket.recvfrom(1027)

    # Unwrap the received packet.
    packet_nr = int.from_bytes(message[0:2], 'big')
    flag = int.from_bytes(message[2:3], 'big')
    chunk = message[3:]

    # Send the ACK for the packet to the Sender (regardless whether it's the first
    # time the packet is received or not).
    serverSocket.sendto(message[0:2], clientAddress)

    # Crude package duplication handling.
    # If the package was received previously, "discard" the chunk.
    if packet_nr not in chunks_dict:
        chunks_dict[packet_nr] = chunk

    # logging.info("Packet " + str(packet_nr) + " received.")
    if flag == 1:
        # Last packet detected; we can extract the max nr of packets from here.
        nr_sent_packets = packet_nr + 1

        # logging.info("Last sent packet received.")

        # Resend the ACK for the last packet several times.

        # In this stop-and-wait protocol, if packet n was received it means that the sender
        # received ACKs for all the packets up to n-1.

        # Ergo, if the last packet is received, all the ACKs for the previous packets
        # have been successfully received.
        for ii in range(resend_last_packet_n_times):
            serverSocket.sendto(message[0:2], clientAddress)
        serverSocket.close()
        break
        # logging.info("All packets have been received.")
    
# logging.info("Reconstructing file.")
with open(fileName, 'wb') as f:
    for ii in range(nr_sent_packets):
        f.write(chunks_dict[ii])
# logging.info("File saved.")
