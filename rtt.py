import os
import telnetlib
from time import sleep
import numpy as np

class RTT:
    def __init__(self, host='localhost', port=19021):
        self._rtt_instance = telnetlib.Telnet(host, port)
        temp = self._rtt_instance.read_until(b'.exe\r\n')
        self._received_lines = list()
        self._received_lines.append(temp.decode('ascii'))
        self._received_fresh_point = 0
        self._arrival_callback = None

    def set_callback(self, func):
        self._arrival_callback = func

    def start_daemon(self):
        import threading
        def receive_loop():
            while True:
                try:
                    line = self._rtt_instance.read_until(b'\n')
                    # self._received_lines.append(line.decode('ascii'))
                    if self._arrival_callback:
                        self._arrival_callback(line.decode('ascii'))
                except:
                    print('error while read')
        self._recv_thread = threading.Thread(target = receive_loop, args = ())
        self._recv_thread.setDaemon(True)
        self._recv_thread.start()

    def readline(self):
        if len(self._received_lines) <= self._received_fresh_point:
            return None
        else:
            line = self._received_lines[self._received_fresh_point]
            self._received_fresh_point += 1
            return line

    def writeline(self, line):
        self._rtt_instance.write((line+'\n').encode('ascii'))

    def __del__(self):
        # we close the telnet connection, so that the daemon thread will crash.
        self._rtt_instance.close()

    def test(self):
        while True:
            x = self._rtt_instance.read_some()
            if len(x) == 0:
                continue
            print(len(x), ' '.join(list(map(lambda s:'%02x'%s, x))))

class Machine:
    LOG_DEPTH = 2 * 60 * 50
    def __init__(self, host='localhost', port=19021):
        self.rtt = RTT(host, port)
        self.rtt.start_daemon()
        self.press = 0
        self.pwm = 0;
        self._ready = False
        self.index = 0
        self.press_log = np.zeros(shape=self.LOG_DEPTH, dtype=np.float32)
        def arrival(line):
            import re
            if line.startswith('READY'):
                self._ready = True
            else:
                reg = re.compile("PRESS,(?P<index>[0-9]+),(?P<press>[0-9]+)")
                match = reg.match(line)
                if match:
                    index = int(match.group('index'))
                    if index >= self.LOG_DEPTH:
                        return
                    press = int(match.group('press'))
                    self.press_log[index] = press
                    self.press = press
                    self.index = index
        self.rtt.set_callback(arrival)

    def reset(self):
        self.rtt.writeline("RESET")
        self._ready = False
        self.press = 0
        self.pwm = 0
        self.press_log = np.zeros(shape=self.LOG_DEPTH, dtype=np.float32)

    def setpwm(self, pwm):
        if pwm > 255:
            pwm = 255
        if pwm < 0:
            pwm = 0
        self.rtt.writeline("SETPWM,%d" % pwm)
        self.pwm = pwm

    @property
    def ready(self):
        return self._ready
