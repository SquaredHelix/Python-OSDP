class MockSerial:
    in_waiting: int = 0

    def __init__(self, file_path):
        self.buffer = []
        self.pos = 0
        with open(file_path, "r") as f:
            for line in f:
                line = line.split("#")[0].strip()
                if not line:
                    continue
                for b in line.split():
                    self.buffer.append(int(b, 16))
        self.in_waiting = len(self.buffer)

    def write(self, data: bytes) -> int:
        print("Sending data:")
        readable = ""
        for d in data:
            char = hex(d).replace("0x", "")
            if len(char) == 1:
                char = "0" + char
            readable += char + " "
        print(readable)

    def read(self, n: int = 1) -> bytes:
        if self.pos >= len(self.buffer):
            in_waiting = 0
            return b""
        chunk = self.buffer[self.pos:self.pos+n]
        self.pos += len(chunk);
        self.in_waiting -= n
        return bytes(chunk)