"""
Embedded Python Block: WhatsApp GUI (Menu-Based Address Config + TXT Only)
"""

from gnuradio import gr
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import pmt
from datetime import datetime
import base64
import os

# --- 1. VISUAL HELPERS & THEMES ---

THEMES = {
    "light": {
        "bg_color": "#E5DDD5", "top_bar": "#075E54", "input_area": "#F0F0F0",
        "input_box": "#FFFFFF", "text_primary": "black", "bubble_own": "#DCF8C6",
        "bubble_other": "#FFFFFF", "time_color": "gray", "tick_color": "#4DF0F0",
        "border": "#dcdcdc", "dialog_bg": "#FFFFFF"
    },
    "dark": {
        "bg_color": "#0b141a", "top_bar": "#202c33", "input_area": "#202c33",
        "input_box": "#2a3942", "text_primary": "#e9edef", "bubble_own": "#005c4b",
        "bubble_other": "#202c33", "time_color": "#8696a0", "tick_color": "#53bdeb",
        "border": "#202c33", "dialog_bg": "#2a3942"
    }
}

class WallpaperScrollArea(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

class ConfigDialog(QtWidgets.QDialog):
    """ Small popup to change Source and Dest IDs """
    def __init__(self, current_my, current_target, theme_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure IDs")
        self.resize(300, 150)
        self.theme = THEMES[theme_name]
        
        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Inputs
        form_layout = QtWidgets.QFormLayout()
        self.my_input = QtWidgets.QLineEdit(str(current_my))
        self.target_input = QtWidgets.QLineEdit(str(current_target))
        
        lbl_my = QtWidgets.QLabel("My ID (Source):")
        lbl_target = QtWidgets.QLabel("Target ID (Dest):")
        
        form_layout.addRow(lbl_my, self.my_input)
        form_layout.addRow(lbl_target, self.target_input)
        layout.addLayout(form_layout)
        
        # Buttons
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        # Styling
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme['dialog_bg']}; color: {self.theme['text_primary']}; }}
            QLabel {{ color: {self.theme['text_primary']}; font-weight: bold; }}
            QLineEdit {{ 
                background-color: {self.theme['input_box']}; 
                color: {self.theme['text_primary']}; 
                border: 1px solid {self.theme['border']}; 
                padding: 5px; border-radius: 5px;
            }}
            QPushButton {{ 
                background-color: {self.theme['top_bar']}; 
                color: white; border: none; padding: 8px; border-radius: 4px;
            }}
        """)

    def get_values(self):
        try:
            m = int(self.my_input.text())
            t = int(self.target_input.text())
            return m, t
        except ValueError:
            return None, None

class _GuiPoster(QtCore.QObject):
    rx_sig = QtCore.pyqtSignal(str, int)     
    ack_sig = QtCore.pyqtSignal()            
    file_save_sig = QtCore.pyqtSignal(str, str) 
    def __init__(self): super().__init__()

# --- 2. MAIN GUI WINDOW ---

class ChatWindow(QtWidgets.QWidget):
    def __init__(self, send_callback, config_callback, payload_size=32, dest_name="Node A"):
        super(ChatWindow, self).__init__()
        self.send_callback = send_callback
        self.config_callback = config_callback
        self.payload_size = payload_size
        self.dest_name = dest_name
        
        # State tracking for IDs
        self.my_id = 20       # Default
        self.target_id = 15   # Default
        
        self.current_theme = "light" 
        self.chat_history = [] 
        self.pending_confirmations = []
        self.bubble_widgets = [] 

        self.setWindowTitle(f"SDR Chat - {self.dest_name}")
        self.resize(450, 750)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        
        # -- Top Bar --
        self.top_bar = QtWidgets.QFrame()
        top_layout = QtWidgets.QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(15, 10, 5, 10)
        
        self.header_label = QtWidgets.QLabel(f"👤 {self.dest_name}")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        # Dark Mode Toggle
        self.theme_btn = QtWidgets.QPushButton("🌙")
        self.theme_btn.setFixedSize(35, 35)
        self.theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 18px; }")

        # Menu Button (Three Dots)
        self.menu_btn = QtWidgets.QPushButton("⋮")
        self.menu_btn.setFixedSize(35, 35)
        self.menu_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.menu_btn.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; font-size: 24px; color: white; padding-bottom: 5px; }
            QPushButton::menu-indicator { image: none; width: 0px; }
        """)
        
        # --- MENU SETUP ---
        self.menu = QtWidgets.QMenu()
        
        # 1. Configure IDs
        self.config_action = self.menu.addAction("⚙️ Configure IDs")
        self.config_action.triggered.connect(self.open_config_dialog)
        
        self.menu.addSeparator()
        
        # 2. Other actions
        export_action = self.menu.addAction("Export Chat Log")
        clear_action = self.menu.addAction("Clear Chat")
        
        export_action.triggered.connect(self.export_chat)
        clear_action.triggered.connect(self.clear_chat)
        
        self.menu_btn.setMenu(self.menu)
        # ------------------

        top_layout.addWidget(self.header_label)
        top_layout.addStretch()
        top_layout.addWidget(self.theme_btn)
        top_layout.addWidget(self.menu_btn)
        self.main_layout.addWidget(self.top_bar)

        # -- Chat Area --
        self.scroll_area = WallpaperScrollArea() 
        self.chat_container = QtWidgets.QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(QtCore.Qt.AlignTop)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_area.setWidget(self.chat_container)
        self.main_layout.addWidget(self.scroll_area)

        # -- Input Area --
        self.input_frame = QtWidgets.QFrame()
        input_layout = QtWidgets.QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        self.emoji_btn = QtWidgets.QPushButton("😊")
        self.emoji_btn.setFixedSize(40, 40)
        self.emoji_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.emoji_btn.setStyleSheet("""QPushButton { border: none; font-size: 20px; } QPushButton::menu-indicator { image: none; width: 0px; }""")
        
        self.emoji_menu = QtWidgets.QMenu()
        emojis = ["😀", "😂", "👍", "❤️", "📻", "🛰️", "👋", "✅", "⚠️", "🔥"]
        for e in emojis:
            action = self.emoji_menu.addAction(e)
            action.triggered.connect(lambda checked, emo=e: self.input_box.insert(emo))
        self.emoji_btn.setMenu(self.emoji_menu)

        self.file_btn = QtWidgets.QPushButton("📎")
        self.file_btn.setFixedSize(40, 40)
        self.file_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.file_btn.setStyleSheet("border: none; font-size: 20px;")
        self.file_btn.clicked.connect(self.handle_file_click)
        
        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.returnPressed.connect(self.handle_send_click)
        
        self.send_btn = QtWidgets.QPushButton("➤")
        self.send_btn.setFixedSize(45, 45)
        self.send_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton { background-color: #128C7E; color: white; border-radius: 22px; font-size: 18px; border: none; }
            QPushButton:hover { background-color: #075E54; }
        """)
        self.send_btn.clicked.connect(self.handle_send_click)

        input_layout.addWidget(self.emoji_btn)
        input_layout.addWidget(self.file_btn)
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.send_btn)
        self.main_layout.addWidget(self.input_frame)

        self.apply_theme()

    def open_config_dialog(self):
        """ Opens the dialog to change IDs via the menu """
        dlg = ConfigDialog(self.my_id, self.target_id, self.current_theme, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_my, new_target = dlg.get_values()
            if new_my is not None and new_target is not None:
                self.update_ids(new_my, new_target)

    def update_ids(self, my_id, target_id):
        self.my_id = my_id
        self.target_id = target_id
        
        # Create PMT dict for config
        cfg = pmt.make_dict()
        cfg = pmt.dict_add(cfg, pmt.intern("my_addr"), pmt.from_long(my_id))
        cfg = pmt.dict_add(cfg, pmt.intern("dest_addr"), pmt.from_long(target_id))
        
        # Send config to blocks
        self.config_callback(cfg)
        
        # Update UI
        self.dest_name = f"Node {target_id}"
        self.header_label.setText(f"👤 {self.dest_name}")
        self._add_bubble(f"🔁 System: Updated IDs.\nMy ID: {my_id}\nTarget ID: {target_id}", True, "SYS")

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme_btn.setText("☀️" if self.current_theme == "dark" else "🌙")
        self.apply_theme()

    def apply_theme(self):
        t = THEMES[self.current_theme]
        self.setStyleSheet(f"QWidget {{ font-family: 'Segoe UI', sans-serif; color: {t['text_primary']}; }}")
        self.top_bar.setStyleSheet(f"background-color: {t['top_bar']}; border: none;")
        self.scroll_area.setStyleSheet(f"border: none; background-color: {t['bg_color']};")
        self.input_frame.setStyleSheet(f"background-color: {t['input_area']}; border-top: 1px solid {t['border']};")
        self.input_box.setStyleSheet(f"""
            QLineEdit {{ background-color: {t['input_box']}; color: {t['text_primary']}; border: 1px solid {t['border']}; border-radius: 20px; padding: 10px; }}
        """)
        for w in self.bubble_widgets:
            self._style_bubble(w['bubble'], w['stack'], w['ts'], w['is_own'])

    def _style_bubble(self, bubble_lbl, stack_widget, time_lbl, is_own):
        t = THEMES[self.current_theme]
        bg = t['bubble_own'] if is_own else t['bubble_other']
        bubble_lbl.setStyleSheet(f"background-color: transparent; color: {t['text_primary']}; font-size: 14px;")
        stack_widget.setStyleSheet(f"background-color: {bg}; border-radius: 10px; border: 1px solid {t['border']};")
        current_text = time_lbl.text()
        if "✓✓" in current_text and ("#4DF0F0" in current_text or "#53bdeb" in current_text): pass 
        else: time_lbl.setStyleSheet(f"color: {t['time_color']}; font-size: 11px; margin-top: 4px; background-color: transparent;")

    def export_chat(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Chat Log", "", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"--- Chat Log with {self.dest_name} ---\n")
                    for msg in self.chat_history:
                        sender = "ME" if msg['is_own'] else self.dest_name
                        f.write(f"[{msg['time']}] {sender}: {msg['text']}\n")
            except: pass

    def clear_chat(self):
        self.chat_history = []
        self.pending_confirmations = []
        self.bubble_widgets = []
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def handle_send_click(self):
        text = self.input_box.text()
        if not text: return
        self._process_outgoing(text, is_file=False)
        self.input_box.clear()

    def handle_file_click(self):
        # 1. Update filter to suggest .txt files
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Text File", "", "Text Files (*.txt);;All Files (*)")
        if not path: return
        
        filename = os.path.basename(path)

        # 2. VALIDATION: Check if it ends with .txt
        if not filename.lower().endswith(".txt"):
            # Display System Error Bubble
            self._add_bubble(f"⚠️ System: Only .txt files are supported!\nYou selected: {filename}", True, "SYS")
            return

        # 3. Proceed if valid
        try:
            with open(path, "rb") as f: 
                b64 = base64.b64encode(f.read()).decode('utf-8')
            self._process_outgoing(f"FILE:{filename}:{b64}", is_file=True, filename=filename)
        except: pass

    def _process_outgoing(self, data_str, is_file=False, filename=""):
        chunk_cap = self.payload_size - 1
        data_len = len(data_str.encode("utf-8", "ignore"))
        num_chunks = (data_len + chunk_cap - 1) // chunk_cap
        if num_chunks == 0: num_chunks = 1
        disp = f"📎 Sending File: {filename}..." if is_file else data_str
        time_str = datetime.now().strftime("%H:%M")
        self.chat_history.append({'text': disp, 'is_own': True, 'time': time_str})
        ts = self._add_bubble(disp, is_own=True, time_str=time_str)
        self.pending_confirmations.append({'widget': ts, 'remaining': num_chunks, 'completed': False})
        self.send_callback(data_str)

    def on_rx_message(self, text, seq):
        disp = text
        if text.startswith("FILE:"):
            try: disp = f"📎 Received File: {text.split(':', 2)[1]} (Saved)"
            except: disp = "📎 Received Corrupted File"
        time_str = datetime.now().strftime("%H:%M")
        self.chat_history.append({'text': disp, 'is_own': False, 'time': time_str})
        self._add_bubble(disp, is_own=False, time_str=time_str)

    def on_ack_received(self):
        for item in self.pending_confirmations:
            if not item['completed']:
                if item['remaining'] > 0:
                    item['remaining'] -= 1
                    if item['remaining'] == 0:
                        item['completed'] = True
                        t = THEMES[self.current_theme]
                        now = datetime.now().strftime("%H:%M")
                        item['widget'].setText(f"{now} <span style='color: {t['tick_color']}; font-weight: bold;'>✓✓</span>")
                return

    def _add_bubble(self, text, is_own, time_str):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0,0,0,0)
        bubble = QtWidgets.QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        
        ts_html = f"{time_str} <span style='color: gray; font-weight: bold;'>✓✓</span>" if is_own else time_str
        ts = QtWidgets.QLabel(ts_html)
        ts.setAlignment(QtCore.Qt.AlignRight)
        ts.setTextFormat(QtCore.Qt.RichText)

        stack = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(stack)
        vbox.setContentsMargins(8,8,8,5)
        vbox.addWidget(bubble)
        vbox.addWidget(ts)
        
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        shadow.setColor(QtGui.QColor(0, 0, 0, 40))
        stack.setGraphicsEffect(shadow)

        self._style_bubble(bubble, stack, ts, is_own)
        self.bubble_widgets.append({'bubble': bubble, 'stack': stack, 'ts': ts, 'is_own': is_own})

        if is_own: 
            layout.addStretch()
            layout.addWidget(stack)
        else: 
            layout.addWidget(stack)
            layout.addStretch()
        self.chat_layout.addWidget(row)
        QtWidgets.QApplication.processEvents()
        QtCore.QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        return ts

# --- 3. GNU RADIO BLOCK ---

class chat_gui_block(gr.basic_block):
    def __init__(self, payload_size=32):
        gr.basic_block.__init__(self, name="WhatsApp Chat GUI", in_sig=None, out_sig=None)
        self.payload_size = payload_size
        self.rx_buffer = b""            
        self.last_radio_seq_seen = -1 
        self.last_ack_val_seen = -1
        self.dummy_seq = 0
        
        # Message Ports
        self.message_port_register_out(pmt.intern("out"))
        self.message_port_register_in(pmt.intern("in"))      
        self.message_port_register_in(pmt.intern("ack_in"))
        self.message_port_register_out(pmt.intern("config_out")) # Config Port
        
        self.set_msg_handler(pmt.intern("in"), self.handle_rx_msg)
        self.set_msg_handler(pmt.intern("ack_in"), self.handle_ack_msg)
        
        self._poster = _GuiPoster()
        self.qapp = QtWidgets.QApplication.instance()
        if not self.qapp: self.qapp = QtWidgets.QApplication(sys.argv)
        
        # GUI
        self.gui = ChatWindow(self.send_pdus, self.publish_config, payload_size=self.payload_size, dest_name=str(0))
        
        self._poster.rx_sig.connect(self.gui.on_rx_message)
        self._poster.ack_sig.connect(self.gui.on_ack_received)
        self._poster.file_save_sig.connect(self._save_file_on_disk)
        self.gui.show()

    def publish_config(self, pmt_msg):
        self.message_port_pub(pmt.intern("config_out"), pmt_msg)

    def send_pdus(self, text):
        data = text.encode("utf-8", "ignore")
        chunk_size = self.payload_size - 1
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        if not chunks: chunks = [b'']
        for i, chunk in enumerate(chunks):
            header = 0x01 if i == len(chunks) - 1 else 0x00
            payload = bytes([header]) + chunk
            if len(payload) < self.payload_size: payload += b'\x00' * (self.payload_size - len(payload))
            meta = pmt.make_dict()
            pmt.dict_add(meta, pmt.intern("seq"), pmt.from_long(self.dummy_seq))
            self.dummy_seq = (self.dummy_seq + 1) % 256
            vec = pmt.init_u8vector(len(payload), list(payload))
            self.message_port_pub(pmt.intern("out"), pmt.cons(meta, vec))

    def handle_rx_msg(self, pdu):
        if not pmt.is_pair(pdu): return
        meta = pmt.car(pdu)
        payload = pmt.cdr(pdu)
        if not pmt.is_u8vector(payload): return
        seq = -1
        if pmt.dict_has_key(meta, pmt.intern("seq")):
            try: seq = pmt.to_python(pmt.dict_ref(meta, pmt.intern("seq"), pmt.PMT_NIL))
            except: pass
        if seq != -1:
            if seq == self.last_radio_seq_seen: return 
            self.last_radio_seq_seen = seq
        data = bytes(pmt.u8vector_elements(payload))
        if len(data) > 0:
            header, content = data[0], data[1:]
            self.rx_buffer += content.rstrip(b'\x00')
            if header == 0x01:
                try:
                    txt = self.rx_buffer.decode('utf-8', 'ignore')
                    self._poster.rx_sig.emit(txt, seq)
                    if txt.startswith("FILE:"):
                        parts = txt.split(":", 2)
                        self._poster.file_save_sig.emit(parts[1], parts[2])
                except: pass
                self.rx_buffer = b""

    def handle_ack_msg(self, pdu):
        if not pmt.is_pair(pdu): return
        meta = pmt.car(pdu)
        payload = pmt.cdr(pdu)
        ack_seq = -1
        if pmt.dict_has_key(meta, pmt.intern("ack")):
            try: ack_seq = pmt.to_python(pmt.dict_ref(meta, pmt.intern("ack"), pmt.PMT_NIL))
            except: pass
        elif pmt.is_u8vector(payload):
            data = bytes(pmt.u8vector_elements(payload))
            if len(data) > 0: ack_seq = int(data[0])
        if ack_seq != -1:
            if ack_seq == self.last_ack_val_seen: return
            self.last_ack_val_seen = ack_seq
            self._poster.ack_sig.emit()

    def _save_file_on_disk(self, fname, b64_data):
        # 1. Get the Target Node ID from the GUI
        # This gets the ID of the person you are chatting with
        node_id = self.gui.target_id 
        
        # 2. Create a dynamic folder name (e.g., "downloads_node_20")
        folder_name = f"downloads_node_{node_id}"
        
        # 3. Create the directory if it doesn't exist
        if not os.path.exists(folder_name): 
            os.makedirs(folder_name)
            
        # 4. Save the file inside that specific folder
        try:
            full_path = os.path.join(folder_name, fname)
            with open(full_path, "wb") as f: 
                f.write(base64.b64decode(b64_data))
            print(f"[System] File saved to: {full_path}")
        except Exception as e: 
            print(f"[System] Error saving file: {e}")

    def stop(self):
        self.gui.close()
        return super().stop()