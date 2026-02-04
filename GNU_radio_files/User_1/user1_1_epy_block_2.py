"""
Embedded Python Block: Address Filter (DATA Only) - Auto-Align
"""
from gnuradio import gr
import pmt

class address_filter_rx(gr.basic_block):
    """
    Scans for [ PREAMBLE ] inside the PDU.
    Expects after preamble: [ DEST(1) | TYPE(1) | SEQ(1) | PAYLOAD... ]
    Accepts only if DEST == my_addr AND TYPE == 0x01
    """

    def __init__(self, preamble_len=32):
        gr.basic_block.__init__(self, name="Address Filter", in_sig=None, out_sig=None)
        
        self.my_addr = 0 & 0xFF
        
        # Exact 128-byte Preamble (Must match TX)
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

        # 1. SEARCH for the preamble pattern to find exact start
        start_idx = data.find(self.preamble)
        if start_idx == -1:
            self._emit_drop(meta, data, reason="preamble_not_found")
            return

        # 2. Identify the packet content after the preamble
        # Structure: [DEST(1)] [TYPE(1)] [SEQ(1)] ...
        payload_idx = start_idx + len(self.preamble)
        
        # Check if we have enough bytes remaining for Dest+Type
        if len(data) < payload_idx + 2:
            self._emit_drop(meta, data, reason="short_after_preamble")
            return

        frame = data[payload_idx:]
        
        dest = frame[0]
        msg_type = frame[1]

        # 3. Check Address
        if dest != self.my_addr:
            self._emit_drop(meta, data, reason="addr_mismatch")
            return

        # 4. Check Type (Must be 0x01 for Data)
        if msg_type != 0x01:
            return # Silently ignore ACKs or others

        # 5. Strip Dest(1) + Type(1) -> Keep [ SEQ | PAYLOAD | CRC ]
        fwd = frame[2:]
        
        if len(fwd) < 1: 
            return

        seq = fwd[0]

        # Publish
        try:
            meta = pmt.dict_add(meta, pmt.intern("dest_addr"), pmt.from_long(dest))
            meta = pmt.dict_add(meta, pmt.intern("seq"), pmt.from_long(seq))
        except: pass

        out_vec = pmt.init_u8vector(len(fwd), list(fwd))
        self.message_port_pub(pmt.intern('out'), pmt.cons(meta, out_vec))

    def _emit_drop(self, meta, data_bytes, reason="drop"):
        try:
            m = pmt.dict_add(meta, pmt.intern("drop_reason"), pmt.intern(reason))
            v = pmt.init_u8vector(len(data_bytes), list(data_bytes))
            self.message_port_pub(pmt.intern('drop'), pmt.cons(m, v))
        except: pass