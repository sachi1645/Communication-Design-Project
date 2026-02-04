from gnuradio import gr
import pmt, zlib

class ack_crc32_verify_minimal(gr.basic_block):
    """
    ACK CRC32 Verify (Minimal, 1-byte ACK)
    -------------------------------------
    Input PDU (port 'in'):
        Payload: [ NEXT_SEQ(1B) | PAYLOAD(40B) | CRC32(4B, big-endian) ]
        CRC over: [ NEXT_SEQ | PAYLOAD ]  (1 + 40 = 41 bytes)

    On CRC pass:
        → 'ack_out': PDU with
             meta:    { ack: NEXT_SEQ, crc_ok: True }
             payload: [ NEXT_SEQ ]  (1 byte)

    On CRC fail:
        → 'drop': PDU with original frame and meta:
             { crc_ok: False, drop_reason: "crc_fail" or "bad_len" }

    Parameters
      variant : "ieee"  (init/xor=0xFFFFFFFF, reflected)
                "zlib"  (init/xor=0x00000000, reflected)
    """

    def __init__(self, variant="ieee"):
        gr.basic_block.__init__(self,
                                name="CRC32 Verifier ACK",
                                in_sig=None,
                                out_sig=None)

        self.variant = str(variant).lower().strip()
        if self.variant not in ("ieee", "zlib"):
            self.variant = "ieee"

        # Expected payload layout: 1 (next_seq) + 40 (payload) + 4 (crc32)
        self.payload_len = 40

        # Ports
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

        self.message_port_register_out(pmt.intern("ack_out"))
        self.message_port_register_out(pmt.intern("drop"))

    # --- CRC helper ---
    def _crc32(self, data: bytes) -> int:
        if self.variant == "ieee":
            # CRC-32/IEEE 802.3: reflected, init=0xFFFFFFFF, xorout=0xFFFFFFFF
            return (zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF) & 0xFFFFFFFF
        else:
            # zlib default: reflected, init=0x00000000, xorout=0x00000000
            return zlib.crc32(data) & 0xFFFFFFFF

    # --- main handler ---
    def _handle(self, pdu):
        if not pmt.is_pair(pdu):
            return

        meta, pl = pmt.car(pdu), pmt.cdr(pdu)
        if not pmt.is_u8vector(pl):
            return

        buf = bytes(pmt.u8vector_elements(pl))

        # Expect exactly NEXT_SEQ(1) + PAYLOAD(40) + CRC32(4) = 45 bytes
        expected_len = 1 + self.payload_len + 4
        if len(buf) != expected_len:
            self._emit_drop(meta, buf, "bad_len")
            return

        body   = buf[:-4]                         # [ NEXT_SEQ | PAYLOAD(40B) ]
        crc_rx = int.from_bytes(buf[-4:], "big")
        next_seq = body[0]

        if self._crc32(body) != crc_rx:
            self._emit_drop(meta, buf, "crc_fail")
            return

        # --- Publish 1-byte ACK PDU ---
        ack_meta = pmt.make_dict()
        try:
            ack_meta = pmt.dict_add(ack_meta, pmt.intern("ack"),
                                    pmt.from_long(int(next_seq)))
            ack_meta = pmt.dict_add(ack_meta, pmt.intern("crc_ok"),
                                    pmt.from_bool(True))
        except Exception:
            pass

        ack_payload = [int(next_seq) & 0xFF]
        self.message_port_pub(
            pmt.intern("ack_out"),
            pmt.cons(ack_meta, pmt.init_u8vector(1, ack_payload))
        )

    def _emit_drop(self, meta, data_bytes, reason):
        try:
            m = meta
            if not pmt.is_dict(m):
                m = pmt.make_dict()
            m = pmt.dict_add(m, pmt.intern("crc_ok"), pmt.from_bool(False))
            m = pmt.dict_add(m, pmt.intern("drop_reason"),
                             pmt.intern(str(reason)))
            v = pmt.init_u8vector(len(data_bytes), list(data_bytes))
            self.message_port_pub(pmt.intern("drop"), pmt.cons(m, v))
        except Exception:
            pass
