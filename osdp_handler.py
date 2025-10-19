
from osdp_messages import *
from typing import Deque
from collections import deque, defaultdict
from typing import Callable, Type, TypeVar, Generic, Dict, List, Optional, Tuple
from dataclasses import dataclass
import traceback
from typing import ClassVar
from serial import Serial
import asyncio
import threading
import time
import datetime

log_raw = False
log_encoded = False

@dataclass
class Frame:
    SOM: ClassVar[int] = 0x53

    addr: int
    length: int
    ctrl: int
    cmd: int
    data: bytes
    is_valid: bool

    def to_bytes(self) -> bytes:
        payload = self.SOM.to_bytes(1)
        payload += self.addr.to_bytes(1)
        payload += self.length.to_bytes(2, 'little')
        payload += self.ctrl.to_bytes(1)
        payload += self.cmd.to_bytes(1)
        payload += self.data
        payload += self.calculate_checksum(payload).to_bytes(1)
        return payload
    
    def to_message(self) -> Tuple[int, int, Message]:
        if not (self.cmd in PROTOCOL_REGISTRY):
            return
        message: Message = PROTOCOL_REGISTRY[self.cmd].from_bytes(self.data)
        return self.addr, self.ctrl, message

    @classmethod
    def generate(cls: Type[T], addr: int, ctrl: int, cmd: int, data: bytes) -> "Frame":
        length = 7 + len(data)
        is_valid = True
        return cls(addr, length, ctrl, cmd, data, is_valid)

    @classmethod
    def from_message(cls: Type[T], addr: int, ctrl: int, message: Message):
        data = message.to_bytes()
        cmd = message.cmd
        return cls.generate(addr, ctrl, cmd, data)

    @classmethod
    def from_bytes(cls: Type[T], payload: bytes) -> "Frame":
        is_valid = True
        som = payload[0]
        if not som == cls.SOM:
            is_valid = False
        addr = payload[1]
        length = int.from_bytes(payload[2:4], 'little')
        ctrl = payload[4]
        use_secure_channel = bool(ctrl & 0x04)
        use_crc= bool(ctrl & 0x02)
        if use_secure_channel or use_crc:
            is_valid = False
        cmd = payload[5]
        data = payload[6:-1]
        trail = payload[-1]
        if not trail == cls.calculate_checksum(payload[:-1]):
            is_valid = False
        return cls(addr, length, ctrl, cmd, data, is_valid)
    
    @classmethod
    def from_serial(cls: Type[T], serial: Serial) -> "Frame":
        payload = serial.read(1)
        som = payload[0]
        if not som == cls.SOM:
            return
        payload += serial.read(3)
        length = int.from_bytes(payload[2:4], 'little')
        if length < 6:
            return
        payload += serial.read(length-4)
        return cls.from_bytes(payload)

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        total = sum(data)
        return (-total) % 256

reader_status = "  "

def handle_led(led: RX_LED):
    color_map = {
        0: "⚫",
        1: "🔴",
        2: "🟢",
        3: "🟡",
        4: "🔵",
    }
    led = color_map.get(led.perm_on_color)
    global reader_status
    reader_status = f"{led}"
    #print(f"\rReader status: [{led}]", end="", flush=True)

class PDSession:
    def __init__(self, handler: "Handler", address: int, message_handler: Callable[["PDSession", Message], None]):
        self.handler = handler
        self.address = address
        self.message_handler = message_handler
        self.initialized = False
        self.poll_queue: Deque[Message] = deque()

    def write(self, message: Message):
        self.handler.write(self.address, message)
    
    def handle_message(self, message: Message):
        self.message_handler(self, message)

def message_handler(session: PDSession, message: Message):
    match message:
        case RX_POLL():
            if (len(session.poll_queue) == 0):
                message = TX_ACK()
                #message.response_bit = 0
                session.write(message)
            else:
                session.write(session.poll_queue.popleft())
        case RX_ID():
            session.initialized = False
            session.write(TX_PDID(0x000001, 1, 1, 0x00000001, "Firmware"))
        case RX_CAP():
            session.initialized = True
            session.write(TX_PDCAP(
                Capability(Capability.FunctionCode.CARD_DATA_FORMAT, 1, 0),
                Capability(Capability.FunctionCode.READER_LED_CONTROL, 1, 2)
            ))
        case RX_LSTAT():
            session.write(TX_LSTATR(0, 0))
            data = 0x12345678.to_bytes(4, 'big')
            session.poll_queue.append(TX_RAW(0, 0, len(data), data))
        case RX_LED() as led:
            handle_led(led)
            session.write(TX_ACK())
        case RX_BUZ():
            session.write(TX_ACK())

class Handler:
    def __init__(self, serial: Serial):
        self.serial = serial
        self.sequence = 0
        self.sessions: Dict[int, PDSession] = defaultdict(dict)

    def start_session(self, address: int, message_handler: Callable[[PDSession, Message], None]):
        session = PDSession(self, address, message_handler)
        self.sessions[address] = session
        return session

    def write(self, addr: int, message: Message):
        response_bit = message.response_bit
        session = self.sessions[addr]
        if (not session.initialized) and isinstance(message, TX_ACK):
            response_bit = 0                                # Controller quirk requires pre-init ACK to set the response bit to 0
        addr = addr | (0x80 * response_bit)                 # Set MSB depending on actual response bit
        ctrl = self.sequence
        frame = Frame.from_message(addr, ctrl, message)
        payload = frame.to_bytes()
        if log_raw:
            print(f"[TX] {payload.hex()} {message.__class__.__name__}")
        if log_encoded:
            print(f"[TX @ {addr % 128}] {message.__class__.__name__} - {message.__dict__}")
        self.serial.write(payload)

    def start(self):
        while True:
            if self.serial.in_waiting:
                frame: Frame = Frame.from_serial(self.serial)
                if frame is None:
                    continue
                if not frame.is_valid:
                    continue
                framed_message = frame.to_message()
                if framed_message is None:
                    continue
                addr, ctrl, message = framed_message
                self.sequence = ctrl

                if addr in range(1, 2):
                    if self.sessions[addr] == {}:
                        self.start_session(addr, message_handler)
                    session = self.sessions[addr]

                    if log_raw:
                        print(f"[RX] {frame.to_bytes().hex()} {message.__class__.__name__}")
                    if log_encoded:
                        print(f"[RX @ {addr}] {message.__class__.__name__} - {message.__dict__}")

                    session.handle_message(message)

def reader_worker(_, stop: threading.Event):
    while True:
        try:
            serial = Serial("/dev/ttySC0", 9600)
            handler = Handler(serial)
            handler.start()
        except Exception as ex:
            print(f'Exception: {ex}')
            traceback.print_exc()

threads = []

stop = threading.Event()
t = threading.Thread(target=reader_worker, args=({}, stop), daemon=True)
threads.append(t)

def led_worker(_, stop: threading.Event):
    while True:
        print(f"\rREADER LED: {reader_status}    UPDATED: {datetime.datetime.now()}", end="", flush=True)
        time.sleep(0.01)

stop2 = threading.Event()
t2 = threading.Thread(target=led_worker, args=({}, stop2), daemon=True)
threads.append(t2)

for t in threads:
    t.start()

for t in threads:
    t.join()

while True:
    pass