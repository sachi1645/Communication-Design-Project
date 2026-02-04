"""
Embedded Python Block: Add Preamble + Address + Type (DATA)
"""
from gnuradio import gr
import pmt

class add_address_block(gr.basic_block):
    """
    Adds [ PREAMBLE(32) | DEST(1) | TYPE(1) ] to payload.
    TYPE = 0x01 (Data)
    """

    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="Add Preamble + Address",
            in_sig=None,
            out_sig=None
        )

        # Initial Address (can be updated dynamically)
        self.address = 0 & 0xFF

        # Fixed 128-Byte Preamble
        self.preamble = [
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
        ]

        # Message ports
        self.message_port_register_in(pmt.intern('in'))
        self.message_port_register_out(pmt.intern('out'))
        self.message_port_register_in(pmt.intern('config'))
        
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
        self.set_msg_handler(pmt.intern('config'), self.handle_config)

    def handle_config(self, msg):
        if pmt.is_dict(msg) and pmt.dict_has_key(msg, pmt.intern("dest_addr")):
            new_addr = pmt.to_long(pmt.dict_ref(msg, pmt.intern("dest_addr"), pmt.PMT_NIL))
            self.address = new_addr & 0xFF

    def handle_msg(self, pdu):
        if not pmt.is_pair(pdu):
            return

        meta = pmt.car(pdu)
        payload = pmt.cdr(pdu)

        if not pmt.is_u8vector(payload):
            return

        data = list(pmt.u8vector_elements(payload))

        # --- MODIFIED HERE ---
        # Structure: [ PREAMBLE ] + [ DEST ] + [ TYPE=0x01 ] + [ DATA ]
        new_data = self.preamble + [self.address] + [0x01] + data

        new_payload = pmt.init_u8vector(len(new_data), new_data)

        # Update metadata
        try:
            meta = pmt.dict_add(meta, pmt.intern("dest_addr"), pmt.from_long(self.address))
        except:
            pass

        self.message_port_pub(pmt.intern('out'), pmt.cons(meta, new_payload))