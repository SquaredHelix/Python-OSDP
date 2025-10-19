from typing import Type, TypeVar
from enum import IntEnum
import math

PROTOCOL_REGISTRY = {}

# Decorator for mapping 
def osdp_id(cmd: int, response_bit: int):
    def decorator(cls):
        cls.cmd = cmd
        cls.response_bit = response_bit
        PROTOCOL_REGISTRY[cmd] = cls
        return cls
    return decorator

T = TypeVar('T', bound='Message')

class Message:
    def to_bytes(self) -> bytes:
        return b''

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        return cls()

class Capability:
    class FunctionCode(IntEnum):
        CONTACT_STATUS_MONITORING = 1
        OUTPUT_CONTROL = 2
        CARD_DATA_FORMAT = 3
        READER_LED_CONTROL = 4
        READER_AUDIBLE_OUTPUT = 5
        READER_TEXT_OUTPUT = 6
        TIME_KEEPING = 7
        CHECK_CHARACTER_SUPPORT = 8
        COMMUNICATION_SECURITY = 9
        RECEIVE_BUFFERSIZE = 10
        LARGEST_COMBINED_MESSAGE_SIZE = 11
        SMART_CARD_SUPPORT = 12
        READERS = 13
        BIOMETRICS = 14

    def __init__(self, function_code: FunctionCode, compliance_level: int, number_of: int):
        self.function_code = function_code
        self.compliance_level = compliance_level
        self.number_of = number_of

@osdp_id(0x60, 0)
class RX_POLL(Message):
    pass

@osdp_id(0x61, 0)
class RX_ID(Message):
    pass

@osdp_id(0x62, 0)
class RX_CAP(Message):
    pass

@osdp_id(0x69, 0)
class RX_LED(Message):
    def __init__(self, reader_number: int, led_number: int, temp_control_code: int, temp_on_time: int, 
                 temp_off_time: int, temp_on_color: int, temp_off_color: int, temp_timer_lsb: int, temp_timer_msb: int,
                 perm_control_code: int, perm_on_time: int, perm_off_time: int, perm_on_color: int, perm_off_color: int):
        self.reader_number = reader_number
        self.led_number = led_number
        self.temp_control_code = temp_control_code
        self.temp_on_time = temp_on_time
        self.temp_off_time = temp_off_time
        self.temp_on_color = temp_on_color
        self.temp_off_color = temp_off_color
        self.temp_timer_lsb = temp_timer_lsb
        self.temp_timer_msb = temp_timer_msb
        self.perm_control_code = perm_control_code
        self.perm_on_time = perm_on_time
        self.perm_off_time = perm_off_time
        self.perm_on_color = perm_on_color
        self.perm_off_color = perm_off_color
    
    def to_bytes(self) -> bytes:
        payload = self.reader_number.to_bytes(1, 'big')
        payload += self.led_number.to_bytes(1, 'big')
        payload += self.temp_control_code.to_bytes(1, 'big')
        payload += self.temp_on_time.to_bytes(1, 'big')
        payload += self.temp_off_time.to_bytes(1, 'big')
        payload += self.temp_on_color.to_bytes(1, 'big')
        payload += self.temp_off_color.to_bytes(1, 'big')
        payload += self.temp_timer_lsb.to_bytes(1, 'big')
        payload += self.temp_timer_msb.to_bytes(1, 'big')
        payload += self.perm_control_code.to_bytes(1, 'big')
        payload += self.perm_on_time.to_bytes(1, 'big')
        payload += self.perm_off_time.to_bytes(1, 'big')
        payload += self.perm_on_color.to_bytes(1, 'big')
        payload += self.perm_off_color.to_bytes(1, 'big')
        return payload
    
    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        reader_number = int.from_bytes(data[0:1], 'big')
        led_number = int.from_bytes(data[1:2], 'big')
        temp_control_code = int.from_bytes(data[2:3], 'big')
        temp_on_time = int.from_bytes(data[3:4], 'big')
        temp_off_time = int.from_bytes(data[4:5], 'big')
        temp_on_color = int.from_bytes(data[5:6], 'big')
        temp_off_color = int.from_bytes(data[6:7], 'big')
        temp_timer_lsb = int.from_bytes(data[7:8], 'big')
        temp_timer_msb = int.from_bytes(data[8:9], 'big')
        perm_control_code = int.from_bytes(data[9:10], 'big')
        perm_on_time = int.from_bytes(data[10:11], 'big')
        perm_off_time = int.from_bytes(data[11:12], 'big')
        perm_on_color = int.from_bytes(data[12:13], 'big')
        perm_off_color = int.from_bytes(data[13:14], 'big')
        return cls(reader_number, led_number, temp_control_code, temp_on_time, 
                 temp_off_time, temp_on_color, temp_off_color, temp_timer_lsb, temp_timer_msb,
                 perm_control_code, perm_on_time, perm_off_time, perm_on_color, perm_off_color)

@osdp_id(0x6A, 0)
class RX_BUZ(Message):
    pass

@osdp_id(0x64, 0)
class RX_LSTAT(Message):
    pass

@osdp_id(0x40, 1)
class TX_ACK(Message):
    pass

@osdp_id(0x45, 1)
class TX_PDID(Message):
    def __init__(self, vendor: int, model: int, version: int, serial: int, firmware: str):
        self.vendor = vendor
        self.model = model
        self.version = version
        self.serial = serial
        self.firmware = firmware

    def to_bytes(self) -> bytes:
        payload = self.vendor.to_bytes(3, 'big')
        payload += self.model.to_bytes(1, 'big')
        payload += self.version.to_bytes(1, 'big')
        payload += self.serial.to_bytes(4, 'big')
        payload += self.firmware.encode('ascii')
        return payload
    
    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        vendor = int.from_bytes(data[0:3], 'big')
        model = int.from_bytes(data[3:4], 'big')
        version = int.from_bytes(data[4:5], 'big')
        serial = int.from_bytes(data[5:9], 'big')
        firmware = data[9:].decode('ascii')
        return cls(vendor, model, version, serial, firmware)

@osdp_id(0x46, 1)
class TX_PDCAP(Message):
    def __init__(self, *capabilities: Capability):
        self.capabilities = capabilities
    
    def to_bytes(self) -> bytes:
        payload = b''
        for capability in self.capabilities:
            payload += capability.function_code.to_bytes(1, 'big')
            payload += capability.compliance_level.to_bytes(1, 'big')
            payload += capability.number_of.to_bytes(1, 'big')
        return payload
    
    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        capabilities_count = math.floor(len(data) / 3) # Additional bytes that are not sets of 3 will not be read
        capabilities = []
        for i in range(1, capabilities_count+1):
            start_index = (i * 3) - 3
            function_code = Capability.FunctionCode(int.from_bytes(data[start_index:start_index+1], 'big'))
            compliance_level = int.from_bytes(data[start_index+1:start_index+2], 'big')
            number_of = int.from_bytes(data[start_index+2:start_index+3], 'big')
            capabilities.append(Capability(function_code, compliance_level, number_of))
        return cls(*capabilities)

@osdp_id(0x50, 1)
class TX_RAW(Message):
    def __init__(self, reader_number: int, format_code: int, bit_count, data: bytes):
        self.reader_number = reader_number
        self.format_code = format_code
        self.bit_count = bit_count
        self.data = data

    def to_bytes(self) -> bytes:
        payload = self.reader_number.to_bytes(1, 'big')
        payload += self.format_code.to_bytes(1, 'big')
        payload += self.bit_count.to_bytes(2, 'little')
        payload += self.data
        return payload

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        reader_number = int.from_bytes(data[0:1], 'big')
        format_code = int.from_bytes(data[1:2], 'big')
        bit_count = int.from_bytes(data[2:4], 'little')
        data = data[4:]
        return cls(reader_number, format_code, bit_count, data)

@osdp_id(0x48, 1)
class TX_LSTATR(Message):
    def __init__(self, tamper_status: int, power_status: int):
        self.tamper_status = tamper_status
        self.power_status = power_status
    
    def to_bytes(self) -> bytes:
        payload = self.tamper_status.to_bytes(1)
        payload += self.power_status.to_bytes(1)
        return payload
    
    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        tamper_status = int.from_bytes(data[0:1], 'big')
        power_status = int.from_bytes(data[1:2], 'big')
        return cls(tamper_status, power_status)

#data = 0x12345678.to_bytes(4, 'big')
#le = len(data).to_bytes(2, 'little')
#print(le.hex())
#before_bytes = 0x00.to_bytes(2, 'big') + le + data
#packet = TX_RAW.from_bytes(before_bytes)
#print(packet.__dict__)
#print(before_bytes.hex())
#print(packet.to_bytes().hex())

#data = 0x12345678.to_bytes(4, 'big')
#packet2 = TX_RAW(0, 0, len(data), data)
#print(packet2.__dict__)