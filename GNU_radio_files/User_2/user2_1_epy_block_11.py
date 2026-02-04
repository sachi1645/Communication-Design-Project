from gnuradio import gr
import pmt, zlib

class crc32_verify_and_ack(gr.basic_block):
    """
    CRC32 Verify & ACK
    ----------------------------------------------------------------
    Input  PDU : [ SEQ(1B) | PAYLOAD(40B) | CRC32(4B, big-endian) ]
    PAYLOAD   : [ NONCE(8B) | CIPHERTEXT(32B) ]
    CRC over  : [ SEQ | PAYLOAD ]  -> total 41 bytes

    On CRC pass:
      - 'out'     → PAYLOAD only (40 bytes),
                    meta: {crc_ok=True, seq=<seq>, ...}
      - 'ack_out' → payload: [ NEXT_SEQ(1B) | PAYLOAD(40B) ]  (41 bytes)
                    meta:   {ack=<next_seq>, crc_ok=True}

    On CRC fail:
      - 'drop'    → diagnostic PDU with {crc_ok=False, drop_reason=...}

    Parameters
      variant : "ieee"  (init/xor=0xFFFFFFFF, reflected)
                "zlib"  (init/xor=0x00000000, reflected)
    """

    def __init__(self, variant="ieee"):
        gr.basic_block.__init__(self, name="CRC32 Verifier",
                                in_sig=None, out_sig=None)
        self.variant = str(variant).lower().strip()
        if self.variant not in ("ieee", "zlib"):
            self.variant = "ieee"

        # Fixed payload length: 40 bytes (8B nonce + 32B ciphertext)
        self.payload_len = 40

        # Ports
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self._handle)
        self.message_port_register_out(pmt.intern('out'))      # 40B payload only
        self.message_port_register_out(pmt.intern('ack_out'))  # NEXT_SEQ + PAYLOAD
        self.message_port_register_out(pmt.intern('drop'))     # diagnostics

    # CRC engines
    def _crc32(self, data: bytes) -> int:
        if self.variant == "ieee":
            # CRC-32/IEEE 802.3: reflected, init=0xFFFFFFFF, xorout=0xFFFFFFFF
            return (zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF) & 0xFFFFFFFF
        else:
            # zlib default: reflected, init=0x00000000, xorout=0x00000000
            return zlib.crc32(data) & 0xFFFFFFFF

    def _handle(self, pdu):
        if not pmt.is_pair(pdu):
            return
        meta, pl = pmt.car(pdu), pmt.cdr(pdu)
        if not pmt.is_u8vector(pl):
            return

        buf = bytes(pmt.u8vector_elements(pl))

        # Expect exactly SEQ(1) + PAYLOAD(40) + CRC(4) = 45 bytes
        expected_len = 1 + self.payload_len + 4
        if len(buf) < expected_len:
            self._emit_drop(meta, buf, "short_frame")
            return

        body   = buf[:-4]  # [SEQ | PAYLOAD]
        crc_rx = int.from_bytes(buf[-4:], byteorder='big')

        # Expect exactly 1 + payload_len bytes in body
        if len(body) != 1 + self.payload_len:
            self._emit_drop(meta, buf, "bad_payload_len")
            return

        seq     = body[0]
        payload = body[1:]  # 40 bytes: [NONCE(8) | CIPHERTEXT(32)]

        if self._crc32(body) != crc_rx:
            self._emit_drop(meta, buf, "crc_fail")
            return

        # ---- Publish PAYLOAD only on 'out' (40B) ----
        out_meta = meta
        try:
            out_meta = pmt.dict_add(out_meta, pmt.intern("crc_ok"), pmt.from_bool(True))
            out_meta = pmt.dict_add(out_meta, pmt.intern("seq"),    pmt.from_long(int(seq)))
        except Exception:
            pass

        self.message_port_pub(
            pmt.intern('out'),
            pmt.cons(out_meta, pmt.init_u8vector(len(payload), list(payload)))
        )

        # ---- Publish ACK: [ NEXT_SEQ | PAYLOAD(40B) ] ----
        ack_next = (seq + 1) & 0xFF
        ack_meta = pmt.make_dict()
        try:
            ack_meta = pmt.dict_add(ack_meta, pmt.intern("ack"),    pmt.from_long(ack_next))
            ack_meta = pmt.dict_add(ack_meta, pmt.intern("crc_ok"), pmt.from_bool(True))
        except Exception:
            pass

        ack_bytes = [ack_next] + list(payload)  # 1 + 40 = 41 bytes
        self.message_port_pub(
            pmt.intern('ack_out'),
            pmt.cons(ack_meta, pmt.init_u8vector(len(ack_bytes), ack_bytes))
        )

    def _emit_drop(self, meta, data_bytes, reason):
        try:
            m = meta
            if not pmt.is_dict(m):
                m = pmt.make_dict()
            m = pmt.dict_add(m, pmt.intern("crc_ok"),      pmt.from_bool(False))
            m = pmt.dict_add(m, pmt.intern("drop_reason"), pmt.intern(str(reason)))
            v = pmt.init_u8vector(len(data_bytes), list(data_bytes))
            self.message_port_pub(pmt.intern('drop'), pmt.cons(m, v))
        except Exception:
            pass
