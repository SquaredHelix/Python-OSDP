from osdp import *
from mock import MockSerial
from typing import Deque
from collections import deque
import serial

poll_queue: Deque[Frame] = deque()

serial = MockSerial("mock_serial.txt")
#serial = serial.Serial("COM1", 9600)
handler = Handler(serial)


def poll(frame: Frame):
    if (len(poll_queue) == 0):
        handler.write(Frame(
            0x01, OSDP_PD.ACK, b''
        ))
    else:
        handler.write(poll_queue.popleft())

def id(frame: Frame):
    vendor_code = 0xFFFFFF.to_bytes(3, 'big')
    model_number = (1).to_bytes(1, 'big')
    version = (1).to_bytes(1, 'big')
    serial = 0x00000001.to_bytes(4, 'big')
    firmware = "1.00".encode("ascii")
    handler.write(Frame(
        0x01, OSDP_PD.PDID, vendor_code + model_number + version + serial + firmware
    ))

def cap(frame: Frame):
    card_format = 0x01.to_bytes(1, 'big')
    reader_led = (2).to_bytes(1, 'big')
    reader_buzzer = (0).to_bytes(1, 'big')
    reader_text = (0).to_bytes(1, 'big')
    reader_type = (0).to_bytes(1, 'big')
    input_count = (0).to_bytes(1, 'big')
    output_count = (1).to_bytes(1, 'big')
    event_count = (1).to_bytes(1, 'big')
    multi_part = (1).to_bytes(1, 'big')
    osdp_version = 0x21.to_bytes(1, 'big')
    capabilities_flags = 0x0000.to_bytes(2, 'big')
    handler.write(Frame(
        0x01, OSDP_PD.PDCAP, 
        card_format + reader_led + reader_buzzer + reader_text + reader_type +
        input_count + output_count + event_count + multi_part + osdp_version + capabilities_flags
    ))

def lstat(frame: Frame):
    handler.write(Frame(
        0x01, OSDP_PD.LSTATR, b'\x00'
    ))

def rstat(frame: Frame):
    handler.write(Frame(
        0x01, OSDP_PD.RSTATR, b'\x00'
    ))

def led(frame: Frame):
    handler.write(Frame(
        0x01, OSDP_PD.ACK, b''
    ))

def buz(frame: Frame):
    handler.write(Frame(
        0x01, OSDP_PD.ACK, b''
    ))

def out(frame: Frame):
    handler.write(Frame(
        0x01, OSDP_PD.ACK, b''
    ))

def card_swipe(data: bytes):
    poll_queue.append(Frame(
        0x01, OSDP_PD.RAW, b''
    ))


handler.listen(OSDP_CP.POLL, poll)
handler.listen(OSDP_CP.ID, id)
handler.listen(OSDP_CP.CAP, cap)
handler.listen(OSDP_CP.LSTAT, lstat)
handler.listen(OSDP_CP.RSTAT, rstat)
handler.listen(OSDP_CP.LED, led)
handler.listen(OSDP_CP.BUZ, buz)
handler.listen(OSDP_CP.OUT, out)
handler.start()