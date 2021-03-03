# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
from socket import *

# Initialise the log file.
# logging.basicConfig(filename='Sender1.logs',
#                     filemode='w',
#                     level=logging.INFO)

# Initialise argparser.
parser = argparse.ArgumentParser()
parser.add_argument('RemoteHost', type=str)
parser.add_argument('Port', type=int)
parser.add_argument('FileName', type=str)

# Read arguments.
args = parser.parse_args()
remoteHost = args.RemoteHost
port = args.Port
fileName = args.FileName
# logging.info("Arguments parsed.")

# We can send a maximum number of 2**16 packets (2 bytes).
# Each packet can transmit a maximum of 1024 bytes.
# Therefore, we can only transmit files of size <= 2**26 bytes.
if os.path.getsize(fileName) > 2**26:
    # logging.info("File too large; script finished.")
    sys.exit("File too large.")

# Open up a client socket.
clientSocket = socket(AF_INET, SOCK_DGRAM)

# logging.info("Started sending packets.")
with open(fileName, 'rb') as f:
    # Read the first 1024-bytes chunk from the file to be sent.
    current_chunk = f.read(1024)
    packet_nr = 0

    while(True):
        # Read the next chunk.
        next_chunk = f.read(1024)
        
        # If the current chunk is the last, set the flag to 1. Else, set it to zero.
        flag = 1 if len(next_chunk) == 0 else 0

        # Convert packet_nr to bytes; use Big Endian byte order.
        packet_nr_bytes = packet_nr.to_bytes(2, 'big')

        # Convert flag to bytes; use Big Endian byte order.
        flag_bytes = flag.to_bytes(1, 'big')

        # Create message and send it.
        message = packet_nr_bytes + flag_bytes + current_chunk
        clientSocket.sendto(message, (remoteHost, port))
        # logging.info("Sent packet " + str(packet_nr))

        if len(next_chunk) == 0:
            break
        else:
            current_chunk = next_chunk
            packet_nr += 1

clientSocket.close()
# logging.info("Finished sending all the packets.")
    