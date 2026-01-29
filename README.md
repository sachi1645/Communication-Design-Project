# Two-Way Digital Paging System Using SDRs

**Team SPECACK**
* **Authors:** Dilhara DS, Rahul B, Saruka U, Umair A

---

## 📖 Project Overview
This project implements a **Two-Way Digital Paging System** using **Software Defined Radios (SDR)**. The system is designed to facilitate reliable short message delivery between unique users using digital modulation and error control protocols.

The project leverages **GNU Radio** for signal processing and **Nuand BladeRF** hardware for transmission and reception. It features a custom "WhatsApp-style" GUI for message composition and real-time status updates, bridging the gap between raw RF signals and user-friendly software.

## ✨ Key Features
* **Reliable Communication:** Implements a **Stop-and-Wait ARQ** (Automatic Repeat Request) mechanism. If an Acknowledgment (ACK) is not received within a timeout period, the packet is automatically retransmitted.
* **Digital Modulation:** Utilizes **QPSK (Quadrature Phase Shift Keying)** for efficient data rates and robustness against noise in low SNR conditions.
* **Packetized Data:** Custom packet structure including Preamble, Destination Address, Sequence Number, and Payload.
* **Error Detection:** Integrates **CRC-32** (Cyclic Redundancy Check) to detect and reject corrupted packets.
* **Security (AES-128):** Implements **AES-CTR Encryption** to secure message payloads, preventing unauthorized access and replay attacks via nonces.
* **User-Friendly GUI:** A custom interface allows users to compose messages, attach text files, and view delivery status (sent/delivered ticks) similar to modern messaging apps.

---

## 🛠️ System Architecture

The system is built on a modular architecture using GNU Radio flowgraphs and Python-based control logic.

### 1. Transmitter Chain
The transmitter processes text input into packets through the following stages:
1.  **Packetization:** Converts text to Protocol Data Unit (PDU), adds Sequence Numbers, and manages ARQ logic.
2.  **Encryption:** Encrypts the payload using AES in Counter (CTR) mode.
3.  **Framing:** Appends the Preamble (for synchronization) and Destination Address.
4.  **Modulation:** Maps bits to QPSK symbols and transmits via BladeRF.

### 2. Receiver Chain
The receiver reverses the process to recover the message:
1.  **Synchronization:** Uses Polyphase Clock Sync and Costas Loop for timing and carrier recovery.
2.  **Demodulation:** Decodes QPSK symbols into a bitstream.
3.  **Filtering & Validation:** Checks the Destination Address and verifies data integrity using CRC-32.
4.  **Decryption:** Decrypts the valid payload and displays it in the GUI.

---

## 📦 Packet Structure

The communication relies on a strict packet format to ensure compatibility between nodes:

| Field | Size | Description |
| :--- | :--- | :--- |
| **Preamble** | 128 B | Synchronization and carrier frequency alignment. |
| **Address** | 1 B | Unique device identifier for multi-node support. |
| **Seq Num** | 1 B | Unique ID for tracking and ARQ handling. |
| **Nonce** | 8 B | "Number used once" for AES freshness. |
| **Payload** | 32 B | The encrypted message (Cipher Text). |
| **CRC-32** | 4 B | Error detection checksum. |

---

## 🚀 Protocols Used

### Stop-and-Wait ARQ
To ensure reliability, the sender waits for an ACK packet after every transmission:
1.  Sender transmits a data frame.
2.  Receiver validates the address and CRC.
3.  If validation is successful, the receiver sends an **ACK**.
4.  Sender waits for the ACK. If the timer expires without an ACK, the frame is **re-sent**.

---

## ⚙️ Installation & Requirements

### Hardware Requirements
* **SDR:** Nuand BladeRF (x40 or x115).
* **Antennas:** Suitable ISM band antennas (e.g., 2.4GHz).
* **PC:** Computer capable of running GNU Radio.

### Software Prerequisites
1.  **System Dependencies (Ubuntu/Debian):**
    Ensure you have GNU Radio and BladeRF drivers installed:
    ```bash
    sudo apt-get update
    sudo apt-get install gnuradio gr-osmosdr libbladerf-dev bladeRF
    ```

2.  **Python Dependencies:**
    Install the required libraries for the GUI and Encryption logic:
    ```bash
    pip install -r requirements.txt
    ```

    *Content of `requirements.txt`:*
    * `numpy`
    * `scipy`
    * `PyQt5` (for the GUI)
    * `pycryptodome` (for AES Encryption)

---

## 🏃 Usage

1.  **Connect the BladeRF** to your USB 3.0 port.
2.  **Open the project:**
    ```bash
    python3 CDP_gui.py
    ```
3.  **Configure Node ID:** Set the local address and destination address in the GUI settings.
4.  **Start Messaging:** Type a message and hit send!

---

## 🖼️ Gallery

### GUI Interface
![GUI Screenshot](images/gui_screenshot.png)
*(Placeholder: Upload your GUI screenshot to an 'images' folder and link it here)*

### GNU Radio Flowgraph
![Flowgraph](images/flowgraph_screenshot.png)
*(Placeholder: Upload your GRC flowgraph image here)*
