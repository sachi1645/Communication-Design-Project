from gnuradio import gr
import pmt, threading, time
from collections import deque

class payload_to_pdu_with_seq_arq(gr.basic_block):
    """
    PAYLOAD PDU -> PDU with SEQ + Stop-and-Wait ARQ
    + PRIORITIZATION: Pauses Data TX if an ACK is being sent.
    """

    def __init__(self, payload_size=32, wait_time_s=0.1, max_retries=10, verbose=True):
        gr.basic_block.__init__(self,
                                name="Payload to PDU with SEQ+ARQ (Smart)",
                                in_sig=None,
                                out_sig=None)

        self.payload_size = int(payload_size)
        self.wait_time_s  = float(wait_time_s)
        self.max_retries  = int(max_retries)
        self.verbose      = bool(verbose)

        # --- PORTS ---
        self.message_port_register_in(pmt.intern("in"))       # Data to send
        self.message_port_register_in(pmt.intern("ack_in"))   # ACKs received from other node
        self.message_port_register_in(pmt.intern("busy_in"))  # New: Signal that WE are sending an ACK
        self.message_port_register_out(pmt.intern("out"))     # Final PDU

        self.set_msg_handler(pmt.intern("in"),     self._handle_payload)
        self.set_msg_handler(pmt.intern("ack_in"), self._handle_ack)
        self.set_msg_handler(pmt.intern("busy_in"), self._handle_busy)

        # --- STATE ---
        self._run = threading.Event()
        self._tx_thread = None
        self._seq = 0
        self._last_ack = None
        self._pending_payloads = deque()
        self._payload_cv = threading.Condition()
        self._ack_cv = threading.Condition()
        
        # Smart Backoff State
        self._tx_blocked_until = 0.0

    def start(self):
        self._run.set()
        self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self._tx_thread.start()
        return super().start()

    def stop(self):
        self._run.clear()
        with self._payload_cv: self._payload_cv.notify_all()
        with self._ack_cv: self._ack_cv.notify_all()
        if self._tx_thread: self._tx_thread.join(timeout=1.0)
        return super().stop()

    def _log(self, msg):
        if self.verbose: print(f"[Smart ARQ] {msg}")

    # --- HANDLERS ---
    def _handle_busy(self, pdu):
        """Called when we are sending an ACK. Pause Data TX to avoid collision."""
        # Pause for 150ms to let the ACK clear the radio
        self._tx_blocked_until = time.monotonic() + 0.15 
        # self._log("Prioritizing ACK: Pausing Data TX")

    def _handle_payload(self, pdu):
        if not pmt.is_pair(pdu): return
        meta, pl = pmt.car(pdu), pmt.cdr(pdu)
        if not pmt.is_u8vector(pl): return
        data = bytes(pmt.u8vector_elements(pl))

        # Pad/Truncate
        if len(data) < self.payload_size:
            data = data + b"\x00" * (self.payload_size - len(data))
        elif len(data) > self.payload_size:
            data = data[:self.payload_size]

        with self._payload_cv:
            self._pending_payloads.append(data)
            self._payload_cv.notify()

    def _handle_ack(self, pdu):
        ack_val = None
        if pmt.is_pair(pdu):
            meta = pmt.car(pdu)
            if pmt.is_dict(meta) and pmt.dict_has_key(meta, pmt.intern("ack")):
                try: ack_val = pmt.to_python(pmt.dict_ref(meta, pmt.intern("ack"), pmt.PMT_NIL))
                except: pass
        
        if ack_val is None: # Fallback to payload check
             pl = pmt.cdr(pdu)
             if pmt.is_u8vector(pl):
                 d = bytes(pmt.u8vector_elements(pl))
                 if len(d) >= 1: ack_val = d[0]

        if ack_val is not None:
            with self._ack_cv:
                self._last_ack = ack_val & 0xFF
                self._ack_cv.notify_all()
            self._log(f"Received confirmation ACK={ack_val}")

    # --- TX LOOP ---
    def _tx_loop(self):
        while self._run.is_set():
            # 1. Wait for Data
            with self._payload_cv:
                while self._run.is_set() and not self._pending_payloads:
                    self._payload_cv.wait(timeout=0.1)
                if not self._run.is_set(): break
                payload = self._pending_payloads.popleft()

            # 2. Frame it
            seq = self._seq
            expected_ack = (seq + 1) & 0xFF
            frame = bytes([seq]) + payload
            retries = 0
            got_ack = False

            # 3. Stop-and-Wait Loop
            while self._run.is_set() and not got_ack:
                
                # --- BACKOFF CHECK ---
                # If we are busy sending an ACK (from busy_in), wait here.
                while time.monotonic() < self._tx_blocked_until:
                    time.sleep(0.01)

                # Transmit
                self._publish(frame)
                
                # Wait for ACK
                deadline = time.monotonic() + self.wait_time_s
                while self._run.is_set() and time.monotonic() < deadline:
                    with self._ack_cv:
                        remaining = max(0.0, deadline - time.monotonic())
                        self._ack_cv.wait(timeout=remaining)
                        if self._last_ack == expected_ack:
                            got_ack = True
                            break
                
                if not got_ack:
                    retries += 1
                    if retries > self.max_retries:
                        self._log(f"Dropping seq={seq} after {self.max_retries} retries")
                        got_ack = True # Give up
                    else:
                        self._log(f"Retry {retries} for seq={seq}")

            self._seq = expected_ack

    def _publish(self, frame):
        meta = pmt.make_dict()
        meta = pmt.dict_add(meta, pmt.intern("seq"), pmt.from_long(frame[0]))
        v = pmt.init_u8vector(len(frame), list(frame))
        self.message_port_pub(pmt.intern("out"), pmt.cons(meta, v))