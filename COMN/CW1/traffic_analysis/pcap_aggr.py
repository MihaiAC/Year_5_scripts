from scapy.utils import RawPcapReader
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP
from ipaddress import ip_address, ip_network
import sys
import matplotlib.pyplot as plt


class Node(object):
    def __init__(self, ip, plen):
        self.bytes = plen
        self.left = None
        self.right = None
        self.ip = ip

    def add(self, ip, plen):
        if self.ip == ip:
            self.bytes += plen
        elif self.ip > ip:
            if self.left is None:
                self.left = Node(ip, plen)
            else:
                self.left.add(ip, plen)
        else:
            if self.right is None:
                self.right = Node(ip, plen)
            else:
                self.right.add(ip, plen)

    def data(self, data):
        if self.left:
            self.left.data(data)
        if self.bytes > 0:
            data[ip_network(self.ip)] = self.bytes
        if self.right:
            self.right.data(data)

    @staticmethod
    def supernet(ip1, ip2):
        # arguments are either IPv4Address or IPv4Network
        na1 = ip_network(ip1).network_address
        na2 = ip_network(ip2).network_address

        netmask = 0
        bin1 = format(int(na1), "032b")
        bin2 = format(int(na2), "032b")
        new_bin = ''
        for ii in range(32):
            if bin1[ii] != bin2[ii]:
                break
            else:
                netmask += 1
                new_bin += bin1[ii]
        if netmask == 0:
            na1 = ip_address(0)
        else:
            for ii in range(32-netmask):
                new_bin += '0'
            na1 = ip_address(int(new_bin, 2))
        return ip_network('{}/{}'.format(na1, netmask), strict=False)

    def aggr(self, byte_thresh):
        if self.left is not None:
            self.left.aggr(byte_thresh)
            leftIsLeaf = (self.left.left is None) and (self.left.right is None)
            if self.left.bytes < byte_thresh:
                self.ip = Node.supernet(self.ip, self.left.ip)
                self.bytes += self.left.bytes
                self.left.bytes = 0
                if leftIsLeaf:
                    self.left = None
        if self.right is not None:
            self.right.aggr(byte_thresh)
            rightIsLeaf = (self.right.left is None) and (self.right.right is None)
            if self.right.bytes < byte_thresh:
                self.ip = Node.supernet(self.ip, self.right.ip)
                self.bytes += self.right.bytes
                self.right.bytes = 0
                if rightIsLeaf:
                    self.right = None

class Data(object):
    def __init__(self, data):
        self.tot_bytes = 0
        self.data = {}
        self.aggr_ratio = 0.05
        root = None
        cnt = 0
        for pkt, metadata in RawPcapReader(data):
            ether = Ether(pkt)
            if not 'type' in ether.fields:
                continue
            if ether.type != 0x0800:
                continue
            ip = ether[IP]
            self.tot_bytes += ip.len
            if root is None:
                root = Node(ip_address(ip.src), ip.len)
            else:
                root.add(ip_address(ip.src), ip.len)
            cnt += 1
        root.aggr(self.tot_bytes * self.aggr_ratio)
        root.data(self.data)

    def Plot(self):
        data = {k: v/1000 for k, v in self.data.items()}
        plt.rcParams['font.size'] = 8
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.grid(which='major', axis='y')
        ax.tick_params(axis='both', which='major')
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels([str(l) for l in data.keys()], rotation=45,
                           rotation_mode='default', horizontalalignment='right')
        ax.set_ylabel('Total bytes [KB]')
        ax.bar(ax.get_xticks(), data.values(), zorder=2)
        ax.set_title('IPv4 sources sending {} % ({}KB) or more traffic.'.format(
            self.aggr_ratio * 100, self.tot_bytes * self.aggr_ratio / 1000))
        plt.savefig(sys.argv[1] + '.aggr.pdf', bbox_inches='tight')
        plt.close()


if __name__ == '__main__':
    d = Data(sys.argv[1])
    d.Plot()
