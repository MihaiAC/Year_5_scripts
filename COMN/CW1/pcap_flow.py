from scapy.utils import RawPcapReader
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, TCP
from scapy.layers.inet6 import IPv6
from ipaddress import ip_address, IPv6Address
from socket import IPPROTO_TCP
import sys
import matplotlib.pyplot as plt


class Flow(object):
    def __init__(self, data):
        self.pkts = 0
        self.flows = 0
        self.ft = {}
        for pkt, metadata in RawPcapReader(data):
            self.pkts += 1
            ether = Ether(pkt)
            if ether.type == 0x86dd:
                ip = ether[IPv6]
                tcp_payload_len = ip.plen
            elif ether.type == 0x0800:
                ip = ether[IP]
                tcp_payload_len = ip.len - ip.ihl * 4
            else:
                continue
            
            if not ip.haslayer(TCP):
                    continue
            tcp = ip[TCP]

            src_ip = int(ip_address(ip.src))
            src_port = ip.sport
            dst_ip = int(ip_address(ip.dst))
            dst_port = ip.dport

            key = (src_ip, dst_ip, src_port, dst_port)
            inv_key = (dst_ip, src_ip, dst_port, src_port)
            
            if key in self.ft:
                self.ft[key] += tcp_payload_len
            elif inv_key in self.ft:
                self.ft[inv_key] += tcp_payload_len
            else:
                self.ft[key] = tcp_payload_len

    def Plot(self):
        topn = 100
        data = [i/1000 for i in list(self.ft.values())]
        data.sort()
        data = data[-topn:]
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.hist(data, bins=20, log=True)
        ax.set_ylabel('# of flows')
        ax.set_xlabel('Data sent [KB]')
        ax.set_title('Top {} TCP flow size distribution.'.format(topn))
        plt.savefig(sys.argv[1] + '.flows.pdf', bbox_inches='tight')
        plt.close()


if __name__ == '__main__':
    d = Flow(sys.argv[1])
    d.Plot()
