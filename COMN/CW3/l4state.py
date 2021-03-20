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

class L4State14(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4State14, self).__init__(*args, **kwargs)
        self.ht = set()

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

        tcp_pkt = pkt.get_protocols(tcp.tcp)
        ip_pkt = pkt.get_protocols(ipv4.ipv4)
        # Check if the packet contains a TCP-over-IPV4 packet.
        if tcp_pkt == [] or ip_pkt == []:
            # Negative -> forward the packet to the correct output port.
            if in_port == 1:
                out_port = 2
            else:
                out_port = 1
            acts = [psr.OFPActionOutput(out_port)]
        else:
            # Affirmative -> extract the TCP flow the packet belongs to.
            src_ip = ip_pkt[0].src
            dst_ip = ip_pkt[0].dst
            src_port = tcp_pkt[0].src_port
            dst_port = tcp_pkt[0].dst_port

            # Check if the packet was received on port 1 (the internal port) or on port 2 (the extrenal port).
            if in_port == 1:
                # TCP flow:
                tcp_flow_key = (src_ip, dst_ip, src_port, dst_port)
                # Action: forward it to port 2.
                acts = [psr.OFPActionOutput(2)]
                if tcp_flow_key not in self.ht:
                    # Add flow to ht.
                    self.ht.add(tcp_flow_key)
                    # Add flow to switch's table.
                    mtc = psr.OFPMatch(in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip,
                                       tcp_src=src_port, tcp_dst=dst_port)
                    self.add_flow(dp, 1, mtc, acts, msg.buffer_id)
                    if msg.buffer_id != ofp.OFP_NO_BUFFER:
                        return
            else:
                # Packet was received on port 2.
                tcp_flow_key = (dst_ip, src_ip, dst_port, src_port)
                if tcp_flow_key not in self.ht:
                    # Packet does not match any flow in self.ht -> drop the packet.
                    acts = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
                else:
                    # Packet matches an existing TCP flow.
                    # Forward to port 1 and add to switch flow table (not ht).
                    acts = [psr.OFPActionOutput(1)]
                    # Add to switch flow table:
                    mtc = psr.OFPMatch(in_port=in_port, ipv4_src=src_ip, ipv4_dst=dst_ip,
                                       tcp_src=src_port, tcp_dst=dst_port)
                    self.add_flow(dp, 1, mtc, acts, msg.buffer_id)

                    if msg.buffer_id != ofp.OFP_NO_BUFFER:
                        return
        
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                               in_port=in_port, actions=acts, data=data)
        dp.send_msg(out)
