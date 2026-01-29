# Communication-Design-Project
A robust Two-Way Paging System using SDRs (BladeRF/GNU Radio). Implements QPSK modulation, CRC-32, and Stop-and-Wait ARQ for reliable delivery. Features AES-128 encryption and a custom GUI for secure, real-time wireless messaging between unique nodes.

# Two-Way Digital Paging System Using SDRs

**Authors:** Dilhara DS, Rahul B, Saruka U, Umair A (Team SPECACK)

## 📖 Project Overview
This project implements a **Two-Way Digital Paging System** using **Software Defined Radios (SDR)**. The system is designed to facilitate reliable short message delivery between unique users using digital modulation and error control protocols.

The project leverages **GNU Radio** for signal processing and **BladeRF** hardware for transmission and reception. It features a custom "WhatsApp-style" GUI for message composition and real-time status updates.

## ✨ Key Features
* **Reliable Communication:** Implements a **Stop-and-Wait ARQ** (Automatic Repeat Request) mechanism to ensure packet delivery. If an Acknowledgment (ACK) is not received within a timeout period, the packet is retransmitted.
* **Digital Modulation:** Utilizes **QPSK (Quadrature Phase Shift Keying)** for efficient data rates and robustness against noise in low SNR conditions.
* **Packetized Data:** Custom packet structure including Preamble, Destination Address, Sequence Number, and Payload.
* **Error Detection:** Integrates **CRC-32** (Cyclic Redundancy Check) to detect and reject corrupted packets.
* **Security (Optional):** Implements **AES-CTR Encryption** (128-bit) to secure message payloads, preventing unauthorized access and replay attacks via nonces.
* **User-Friendly GUI:** A custom interface allows users to compose messages, attach text files, and view delivery status (sent/delivered ticks) similar to modern messaging apps.

## 🛠️ System Architecture
The system is built on a modular architecture using GNU Radio flowgraphs.

### Transmitter Chain
The transmitter processes text input into packets through the following stages:
1. **Packetization:** Converts text to PDU, adds Sequence Numbers, and manages ARQ logic.
2. **Encryption:** Encrypts the payload using AES in CTR mode.
3. **Framing:** Appends the Preamble (for synchronization) and Destination Address.
4. **Modulation:** Maps bits to QPSK symbols and transmits via BladeRF.

### Receiver Chain
The receiver reverses the process to recover the message:
1. **Synchronization:** Uses Polyphase Clock Sync and Costas Loop for timing and carrier recovery.
2. **Demodulation:** Decodes QPSK symbols into a bitstream.
3. **Filtering & Validation:** Checks the Destination Address and verifies data integrity using CRC-32.
4. **Decryption:** Decrypts the valid payload and displays it in the GUI.

## 📦 Packet Structure
The communication relies on a strict packet format to ensure compatibility:

| Field | Size | Description |
| :--- | :--- | :--- |
| **Preamble** | 128 B | Synchronization and carrier frequency alignment. |
| **Address** | 1 B | Unique device identifier for multi-node support. |
| **Seq Num** | 1 B | Unique ID for tracking and ARQ handling. |
| **Nonce** | 8 B | "Number used once" for AES freshness. |
| **Payload** | 32 B | The encrypted message (Cipher Text). |
| **CRC-32** | 4 B | Error detection checksum. |

## 🚀 Protocols Used
### Stop-and-Wait ARQ
To ensure reliability, the sender waits for an ACK packet after every transmission.
1. Sender transmits a frame.
2. Receiver validates address and CRC; if successful, sends an ACK.
3. Sender waits for ACK. If the timeout expires, the frame is re-sent.

## 💻 Hardware & Software Requirements
* **Hardware:** Nuand BladeRF (x40/x115).
* **Software:** GNU Radio Companion (GRC).
* **Dependencies:** Python (for custom blocks and GUI), `gr-osmosdr` or `gr-soapy`.
