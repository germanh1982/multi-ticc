from serial import Serial
import logging
from time import sleep, monotonic
import paho.mqtt.client as mqttc
from argparse import ArgumentParser
import yaml

TICCS = ( '/dev/ttyACM0', '/dev/ttyACM1' )

class Ticc:
    EOL = '\r\n'

    def __init__(self, port, timeout, baudrate):
        self._buf = b''
        self._port = port
        self._dev = Serial(port, baudrate, timeout=timeout)

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
    client.connect(cfg['server']['host'])
    client.loop_start()
    log.info("Connected to server.")

    ticcs = [Ticc(device, timeout=cfg['boards']['timeout'], baudrate=cfg['boards']['baudrate']) for device in cfg['boards']['devices']]
    boottime = monotonic()
    log.info(f"Fetching from {len(ticcs)} TICC devices.")

    while True:
        for ticc in ticcs:
            ticc.fetch()
            if monotonic() - boottime < 1:
                ticc.flush()
            
            else:
                for line in ticc.lines():
                    try:
                        chan, meas = line
                    except ValueError:
                        # line has wrong format
                        log.warning(f"Received malformed line: {line}")
                        pass
                    else:
                        log.info(f"New sample: channel={chan} measurement={meas}")
                        client.publish(cfg['topic_template'].format(chan=chan), meas)
        sleep(0.001)

if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument('--loglevel', choices=['debug', 'info', 'warning', 'error', 'critical'], default='debug')
    p.add_argument('configfile')
    args = p.parse_args()

    with open(args.configfile) as fh:
        cfg = yaml.safe_load(fh)

    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%b %d %H:%M:%S', level=args.loglevel.upper())
    log = logging.getLogger(__name__)

    try:
        main()
    except KeyboardInterrupt:
        log.info("Interrupted by user.")

