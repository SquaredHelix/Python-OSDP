from enum import IntEnum
from typing import Protocol, Callable, Dict, List
from dataclasses import dataclass

class Serial(Protocol):
    def write(self, data: bytes) -> int: ...
    def read(self, n: int = 1) -> bytes: ...
    @property
    def in_waiting(self) -> int: ...

# OSDP [CP -> PD] Commands
class OSDP_CP(IntEnum):
    POLL = 0x60             # Poll
    ID = 0x61               # ID Report Request
    CAP = 0x62              # PD Capabilities Request
    LSTAT = 0x64            # Local Status Report Request
    OSTAT = 0x66            # Output Status Report Request
    RSTAT = 0x67            # Reader Status Report Request
    OUT = 0x68              # Output Control Command
    LED = 0x69              # Reader Led Control Command
    BUZ = 0x6A              # Reader Buzzer Control Command
    COMSET = 0x6E           # PD Communication Configuration Command
    KEYSET = 0x75           # Encryption Key Set Command
    CHLNG = 0x76            # Challenge and Secure Session Initialization Request
    SCRYPT = 0x77           # Server Cryptogram
    MFG = 0x80              # Manufacturer Specific Command

# OSDP [PD -> CP] Replies
class OSDP_PD(IntEnum):
    ACK = 0x40              # Command accepted, nothing else to report
    NACK = 0x41             # Command not processed
    PDID = 0x45             # PD ID Report
    PDCAP = 0x46            # PD Capabilities Report
    LSTATR = 0x48           # Local Status Report
    OSTATR = 0x4A           # Output Status Report
    RSTATR = 0x4B           # Reader Status Report
    RAW = 0x50              # Reader Data - Raw bit image of card data
    FMT = 0x51              # Reader Data - Formatted character stream
    KEYPAD = 0x53           # Keypad Data
    COM = 0x54              # PD Communications Configuration Report
    CCRYPT = 0x76           # Client's ID, Random Number, and Cryptogram
    RMAC_I = 0x78           # Initial R-MAC
    BUSY = 0x79             # PD is Busy reply
    MFGREP = 0x90           # Manufacturer Specific Reply

@dataclass                
class Frame:
    ADDR: int
    CMD: OSDP_CP | OSDP_PD
    DATA: bytes

@dataclass
class Header:
    ADDR: int
    LEN_LSB: int
    LEN_MSB: int
    CTRL: int
    CMD: int
    SOM: int = 0x53

def calculate_checksum(data: bytes) -> int:
    total = sum(data)
    return (-total) % 256

def valid_checksum(checksum: int, data: bytes) -> bool:
    return checksum == calculate_checksum(data)


class Handler:
    listeners: Dict[OSDP_CP, List[Callable[[Frame], None]]] = {}

    def __init__(self, serial: Serial):
        self.serial = serial

    def listen(self, command: OSDP_CP, callback: Callable[[Frame], None]):
        self.listeners.setdefault(command, []).append(callback)

    def write(self, frame: Frame):
        total_length = 6 + len(frame.DATA) + 1
        header = Header(
            ADDR=frame.ADDR,
            LEN_LSB=total_length & 0xFF,
            LEN_MSB=(total_length>>8) & 0xFF,
            CTRL=0x00,
            CMD=frame.CMD,
        )
        payload = b''
        payload += header.SOM.to_bytes()
        payload += header.ADDR.to_bytes()
        payload += header.LEN_LSB.to_bytes()
        payload += header.LEN_MSB.to_bytes()
        payload += header.CTRL.to_bytes()
        payload += header.CMD.to_bytes()
        payload += frame.DATA
        payload += calculate_checksum(payload).to_bytes(1)
        self.serial.write(payload)

    def start(self):
        while True:
            if self.serial.in_waiting:
                byte = self.serial.read(1)
                if (byte == Header.SOM.to_bytes()):
                    header = Header(
                        ADDR=self.serial.read(1)[0],
                        LEN_LSB=self.serial.read(1)[0],
                        LEN_MSB=self.serial.read(1)[0],
                        CTRL=self.serial.read(1)[0],
                        CMD=self.serial.read(1)[0]
                    )
                    total_length = header.LEN_LSB + (header.LEN_MSB << 8)
                    bytecount = total_length - 6
                    use_secure_channel = bool(header.CTRL & 0x04)
                    use_crc= bool(header.CTRL & 0x02)
                    if not use_crc and not use_secure_channel:
                        remaining = self.serial.read(bytecount)
                        frame = Frame(header.ADDR, OSDP_CP(header.CMD), remaining[0:bytecount-1])
                        checksum = remaining[bytecount-1]
                        frame_bytes = header.SOM.to_bytes() + header.ADDR.to_bytes() + header.LEN_LSB.to_bytes() + header.LEN_MSB.to_bytes() + header.CTRL.to_bytes() + header.CMD.to_bytes() + frame.DATA 
                        if not valid_checksum(checksum, frame_bytes):
                            print("Invalid checksum!")
                            continue
                        for callback in self.listeners.get(frame.CMD):
                            callback(frame)
                    else:
                        print("Secure channel / crc not implemented")