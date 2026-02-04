"""
Embedded Python Block: ACK Address Filter (ACK Only) - Auto-Align
"""
from gnuradio import gr
import pmt

class ack_address_filter_rx(gr.basic_block):
    """
    Scans for [ PREAMBLE ] inside the PDU.
    Expects: [ DEST(1) | TYPE(1) | NEXT_SEQ(1) | PAYLOAD(40) | CRC(4) ]
    Accepts only if DEST == my_addr AND TYPE == 0x02
    """

    def __init__(self, preamble_len=32):
        gr.basic_block.__init__(self, name="Address Filter ACK", in_sig=None, out_sig=None)

        self.my_addr = 0 & 0xFF
        
        # Exact 128-byte Preamble
        self.preamble = bytes([
            0xD3, 0x42, 0xA1, 0x7F, 0x9C, 0xE2, 0x55, 0xAA,
            0x13, 0x87, 0x4E, 0xB1, 0x2C, 0xF0, 0x99, 0x6D,
            0x3A, 0xC4, 0x1F, 0x82, 0x5B, 0xD8, 0x66, 0xE7,
            0x24, 0x91, 0x7C, 0x0B, 0x38, 0xF2, 0x4D, 0xC6,
            0xD3, 0x42, 0xA1, 0x7F, 0x9C, 0xE2, 0x55, 0xAA,
            0x13, 0x87, 0x4E, 0xB1, 0x2C, 0xF0, 0x99, 0x6D,
            0x3A, 0xC4, 0x1F, 0x82, 0x5B, 0xD8, 0x66, 0xE7,
            0x24, 0x91, 0x7C, 0x0B, 0x38, 0xF2, 0x4D, 0xC6,
            0xD3, 0x42, 0xA1, 0x7F, 0x9C, 0xE2, 0x55, 0xAA,
            0x13, 0x87, 0x4E, 0xB1, 0x2C, 0xF0, 0x99, 0x6D,
            0x3A, 0xC4, 0x1F, 0x82, 0x5B, 0xD8, 0x66, 0xE7,
            0x24, 0x91, 0x7C, 0x0B, 0x38, 0xF2, 0x4D, 0xC6,
            0xD3, 0x42, 0xA1, 0x7F, 0x9C, 0xE2, 0x55, 0xAA,
            0x13, 0x87, 0x4E, 0xB1, 0x2C, 0xF0, 0x99, 0x6D,
            0x3A, 0xC4, 0x1F, 0x82, 0x5B, 0xD8, 0x66, 0xE7,
            0x24, 0x91, 0x7C, 0x0B, 0x38, 0xF2, 0x4D, 0xC6
        ])

        # Length of ACK Frame Content (after preamble)
        # Dest(1) + Type(1) + NextSeq(1) + Payload(40) + CRC(4) = 47 bytes
        self.ACK_CONTENT_LEN = 1 + 1 + 1 + 40 + 4 

        self.message_port_register_in(pmt.intern('in'))
        self.message_port_register_out(pmt.intern('out'))
        self.message_port_register_out(pmt.intern('drop'))
        self.message_port_register_in(pmt.intern('config'))

        self.set_msg_handler(pmt.intern('in'), self._handle)
        self.set_msg_handler(pmt.intern('config'), self.handle_config)

    def handle_config(self, msg):
        if pmt.is_dict(msg) and pmt.dict_has_key(msg, pmt.intern("my_addr")):
            new_addr = pmt.to_long(pmt.dict_ref(msg, pmt.intern("my_addr"), pmt.PMT_NIL))
            self.my_addr = new_addr & 0xFF

    def _handle(self, pdu):
        if not pmt.is_pair(pdu): return
        meta, pl = pmt.car(pdu), pmt.cdr(pdu)
        if not pmt.is_u8vector(pl): return

        data = bytes(pmt.u8vector_elements(pl))
        
        # 1. Search for Preamble
        start_idx = data.find(self.preamble)
        if start_idx == -1:
            return 
            
        payload_idx = start_idx + len(self.preamble)

        # Check length
        if len(data) < payload_idx + self.ACK_CONTENT_LEN:
            return

        # Extract exactly one ACK frame
        frame = data[payload_idx : payload_idx + self.ACK_CONTENT_LEN]

        dest = frame[0]
        msg_type = frame[1]

        # 2. Check Address
        if dest != self.my_addr:
            return

        # 3. Check Type (Must be 0x02 for ACK)
        if msg_type != 0x02:
            return 

        # 4. Strip Dest(1) + Type(1) -> Keep [ NEXT_SEQ | PAYLOAD | CRC ]
        # Offset = 2
        stripped = frame[2:]
        
        next_seq = stripped[0]

        out_meta = meta
        try:
            out_meta = pmt.dict_add(out_meta, pmt.intern("dest_addr"), pmt.from_long(int(dest)))
            out_meta = pmt.dict_add(out_meta, pmt.intern("next_seq"), pmt.from_long(int(next_seq)))
        except: pass

        self.message_port_pub(pmt.intern('out'), pmt.cons(out_meta, pmt.init_u8vector(len(stripped), list(stripped))))

    def _emit_drop(self, meta, bytes_list, reason):
        try:
            m = pmt.dict_add(meta, pmt.intern("drop_reason"), pmt.intern(str(reason)))
            v = pmt.init_u8vector(len(bytes_list), list(bytes_list))
            self.message_port_pub(pmt.intern('drop'), pmt.cons(m, v))
        except: pass