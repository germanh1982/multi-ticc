#!/usr/bin/env python3
from serial import Serial
import logging
from time import sleep, monotonic
import paho.mqtt.client as mqttc

TICCS = ( '/dev/ttyACM0', '/dev/ttyACM1' )

class Ticc:
    EOL = '\r\n'

    def __init__(self, port, timeout):
        self._buf = b''
        self._port = port
        self._dev = Serial(port, baudrate=115200, timeout=timeout)

    def fetch(self):
        to_read = self._dev.in_waiting
        self._buf += self._dev.read(to_read)

    def lines(self):
        for line in (line.decode() for line in self._buf.splitlines(True)):
            if line.endswith(self.EOL):
                self._buf = self._buf[len(line):]
                line = line.rstrip(self.EOL)
                if line.startswith('#') or len(line) == 0:
                    pass
                else:
                    meas, chan = line.split(' ', maxsplit=2)
                    yield (chan, meas)

    def flush(self):
        self._buf = b''

    @property
    def port(self):
        return self._port

def main():
    client = mqttc.Client()
    client.connect('localhost')
    client.loop_start()

    ticcs = []
    for port in TICCS:
        ticcs.append(Ticc(port, timeout=1))

    boottime = monotonic()

    while True:
        for ticc in ticcs:
            ticc.fetch()
            if monotonic() - boottime < 1:
                ticc.flush()
            
            else:
                for line in ticc.lines():
                    chan, meas = line
                    client.publish(f"meas/{chan}", meas)
        sleep(0.001)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)
    main()
