# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
import time
from socket import *

resend_last_packet_n_times = 20

# logging.basicConfig(filename='ZZReceiver3.logs',
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
serverSocket.bind(('localhost', serverPort))
serverSocket.setblocking(0)
# logging.info("Server initialised.")

# The received chunks will be saved in a dictionary.
chunks_dict = dict()
expected_packet_nr = 1

while(True):
    try:
        # Receive packet.
        message, clientAddress = serverSocket.recvfrom(1027)

        # Extract the message ("chunk") and the header from the packet.
        packet_nr = int.from_bytes(message[0:2], 'big')
        flag = int.from_bytes(message[2:3], 'big')
        chunk = message[3:]
        
        # logging.info("Packet " + str(packet_nr) + " received.")
        if packet_nr == expected_packet_nr:
            # If the packet number is the expected one, send an ACK for it.
            v = serverSocket.sendto(expected_packet_nr.to_bytes(2, 'big'), clientAddress)
            # logging.info("ACK for packet: " + str(expected_packet_nr) + " " + str(v))
            chunks_dict[packet_nr] = chunk

            # Increment the expected packet number.
            expected_packet_nr += 1
            if flag == 1:
                # Last packet received AND its number is the expected packet number.
                # This means that the transfer is complete.
                # We need to make sure that at least one ACK for the last packet reaches
                # the Sender.
                # Thus, we send 20 ACKs for the last packet.
                # The probability that they are all lost is 0.05^20=1e-20.
                # logging.info("Last packet received.")
                response_packet_nr = expected_packet_nr - 1
                for ii in range(resend_last_packet_n_times-1):
                    serverSocket.sendto(response_packet_nr.to_bytes(2, 'big'), clientAddress)
                break
        else:
            # Packet number is not the expected one.
            # Send a cumulative ACK for the last (in-order) received packet.
            response_packet_nr = expected_packet_nr - 1
            v = serverSocket.sendto(response_packet_nr.to_bytes(2, 'big'), clientAddress)
            # logging.info("ACK for packet: " + str(response_packet_nr) + " " + str(v))
    except error:
        pass
    
# logging.info("Reconstructing file.")
# Reconstruct and save the file.
with open(fileName, 'wb') as f:
    for ii in range(1, expected_packet_nr):
        f.write(chunks_dict[ii])
# logging.info("File saved.")
serverSocket.close()
