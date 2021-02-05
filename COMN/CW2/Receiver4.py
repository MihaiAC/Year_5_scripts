# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
from socket import *

resend_last_packet_n_times = 15

# TODO: Initialise the log file (for debugging).
logging.basicConfig(filename='Receiver3.logs',
                    filemode='w',
                    level=logging.INFO)

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
logging.info("Arguments parsed.")

# Create server socket.
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))
logging.info("Server initialised.")

# The received chunks will be saved in a dictionary.
chunks_dict = dict()
rcv_base = 0

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

    logging.info("Packet " + str(packet_nr) + " received.")
    if packet_nr == expected_packet_nr:
        serverSocket.sendto(expected_packet_nr.to_bytes(2, 'big'), clientAddress)
        chunks_dict[packet_nr] = chunk
        expected_packet_nr += 1
        if flag == 1:
            # Last packet detected; we can extract the max nr of packets from here.
            # This is not a guarantee that all the packets have been received (we're using UDP).
            logging.info("Last packet received.")
            response_packet_nr = expected_packet_nr - 1
            for ii in range(resend_last_packet_n_times-1):
                serverSocket.sendto(response_packet_nr.to_bytes(2, 'big'), clientAddress)
            break
    else:
        response_packet_nr = expected_packet_nr - 1
        serverSocket.sendto(response_packet_nr.to_bytes(2, 'big'), clientAddress)
    
logging.info("Reconstructing file.")
with open(fileName, 'wb') as f:
    for ii in range(expected_packet_nr):
        f.write(chunks_dict[ii])
logging.info("File saved.")
