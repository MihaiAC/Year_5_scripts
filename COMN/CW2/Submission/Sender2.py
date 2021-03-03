# Mihai Ciobanu s1519734
import os
import sys
import logging
import argparse
import time
from socket import *

# Initialise the log file.
# logging.basicConfig(filename='Sender2.logs',
#                     filemode='w',
#                     level=logging.INFO)

last_packet_max_resends = 5
nr_retransmissions = 0

# Initialise argparser.
parser = argparse.ArgumentParser()
parser.add_argument('RemoteHost', type=str)
parser.add_argument('Port', type=int)
parser.add_argument('FileName', type=str)
parser.add_argument('RetryTimeout', type=int)

# Read arguments.
args = parser.parse_args()
remoteHost = args.RemoteHost
port = args.Port
fileName = args.FileName
timeout = args.RetryTimeout
# logging.info("Arguments parsed.")

# We can send a maximum number of 2**16 packets (2 bytes).
# Each packet can transmit a maximum of 1024 bytes.
# Therefore, we can only transmit files of size <= 2**26 bytes.
if os.path.getsize(fileName) > 2**26:
    # logging.info("File too large; script finished.")
    sys.exit("File too large.")

# Open up a (blocking) client socket.
clientSocket = socket(AF_INET, SOCK_DGRAM)
clientSocket.setsockopt(SOL_SOCKET, SO_SNDBUF, 16384)

# logging.info("Started sending packets.")
transmission_start_time = time.time()
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
        
        resends = 0
        # This loop terminates when the "current_chunk" has been sucessfully sent.
        while(True):
            # Send a packet and wait timeout milliseconds.
            # After timeout milliseconds 
            clientSocket.sendto(message, (remoteHost, port))
            # logging.info("Sent packet " + str(packet_nr))
            clientSocket.settimeout(timeout/1000)
            try:
                # We need to check that the seq number in the ACK corresponds to what
                # we were expecting (can receive ACKs for past resent packets, which were
                # resent too fast).
                while(True):
                    ack_response, server_address = clientSocket.recvfrom(2)
                    if packet_nr != int.from_bytes(ack_response, 'big'):
                        continue
                    else:
                        break
                break

            except error:
                # A timeout ocurred.

                # Increment the number of transmissions.
                nr_retransmissions += 1
                # logging.info("Packet " + str(packet_nr) + " needs to be resent.")

                # Mechanism for correct termination.
                if flag == 1 and resends == last_packet_max_resends:
                    break
                else:
                    resends += 1
        packet_nr += 1
        # If an ACK with flag 1 was received, the transmission is sucessful and can be ended.
        if flag == 1:
            break
        else:
            current_chunk = next_chunk
        resends = 0

transmission_end_time = time.time()
total_transmission_time = transmission_end_time - transmission_start_time
file_size_in_bytes = os.path.getsize(fileName)
print(str(nr_retransmissions) + " " + str(file_size_in_bytes/(1000*total_transmission_time)))
clientSocket.close()
# logging.info("Finished sending all the packets.")
    