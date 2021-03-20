from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet.ether_types import ETH_TYPE_IP

class L4Mirror14(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4Mirror14, self).__init__(*args, **kwargs)
        self.ht = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        acts = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, psr.OFPMatch(), acts)

    def add_flow(self, dp, prio, match, acts, buffer_id=None):
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        bid = buffer_id if buffer_id is not None else ofp.OFP_NO_BUFFER
        ins = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, acts)]
        mod = psr.OFPFlowMod(datapath=dp, buffer_id=bid, priority=prio,
                                match=match, instructions=ins)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port, pkt = (msg.match['in_port'], packet.Packet(msg.data))
        dp = msg.datapath
        ofp, psr, did = (dp.ofproto, dp.ofproto_parser, format(dp.id, '016d'))
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        iph = pkt.get_protocols(ipv4.ipv4)
        tcph = pkt.get_protocols(tcp.tcp)

        out_port = 2 if in_port == 1 else 1
        # Check if the packet contains a TCP-over-IPV4 packet.
        if tcph == [] or iph == []:
            # Negative -> forward the packet to the correct output port.
            acts = [psr.OFPActionOutput(out_port)]
        else:
            # Affirmative -> extract the TCP flow the packet belongs to.
            src_ip = iph[0].src
            dst_ip = iph[0].dst
            src_port = tcph[0].src_port
            dst_port = tcph[0].dst_port

            # Check if the packet was received on port 1 (the internal port) or on port 2 (the extrenal port).
            if in_port == 1:
                # Add flow unconditionally to the switch.

                # Action: forward it to port 2.
                acts = [psr.OFPActionOutput(2)]
                # Add flow to switch's table.
                mtc = psr.OFPMatch(in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip,
                                    tcp_src=src_port, tcp_dst=dst_port, eth_type=eth.ethertype)
                self.add_flow(dp, 1, mtc, acts, msg.buffer_id)
                if msg.buffer_id != ofp.OFP_NO_BUFFER:
                    return
            else:
                # Packet was received on port 2.
                # Check if the received packet has the SYN bit set to 1 and the ACK bit set to 0
                # (which means that the connection is initiated externally.)
                tcp_flow_key = (src_ip, dst_ip, src_port, dst_port)
                if tcph[0].has_flags(tcp.TCP_SYN) and not tcph[0].has_flags(tcp.TCP_ACK):
                    # Add the flow to the dictionary, with a count of 1 and forward the packet
                    # to ports 3 and 1.
                    self.ht[tcp_flow_key] = 1
                    acts = [psr.OFPActionOutput(1), psr.OFPActionOutput(3)]
                elif tcp_flow_key in self.ht:
                    # If this is a flow we are monitoring, increment the number of packets received.
                    self.ht[tcp_flow_key] += 1
                    # Current action.
                    acts = [psr.OFPActionOutput(1), psr.OFPActionOutput(3)]
                    # Future action on encountering a packet from this flow from port 2.
                    acts_from_now_on = [psr.OFPActionOutput(1)]
                    if self.ht[tcp_flow_key] == 10:
                        # Remove the flow entry from the dictionary.
                        del self.ht[tcp_flow_key]
                        # Add the flow to the switch's table.
                        mtc = psr.OFPMatch(in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip,
                                           tcp_src=src_port, tcp_dst=dst_port, eth_type=eth.ethertype)
                        self.add_flow(dp, 1, mtc, acts_from_now_on, msg.buffer_id)

                        if msg.buffer_id != ofp.OFP_NO_BUFFER:
                            return
                else:
                    # This is part of a flow we are NOT monitoring (e.g: initiated by the internal host).
                    # Forward this packet to port 1.
                    acts = [psr.OFPActionOutput(1)]
                    
                    # Add the flow to the switch's table.
                    mtc = psr.OFPMatch(in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip,
                                       tcp_src=src_port, tcp_dst=dst_port, eth_type=eth.ethertype)
                    self.add_flow(dp, 1, mtc, acts, msg.buffer_id)

                    if msg.buffer_id != ofp.OFP_NO_BUFFER:
                        return

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                               in_port=in_port, actions=acts, data=data)
        dp.send_msg(out)
