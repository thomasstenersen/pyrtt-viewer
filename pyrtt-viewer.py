# MIT License
#
# Copyright (c) 2018 Thomas Stenersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#!/usr/bin/env python3

import sys
import time
import threading
import logging
import argparse

try:
    from pynrfjprog.API import API as NrfAPI
    from pynrfjprog.API import DeviceFamily as NrfDeviceFamily
    import pynrfjprog.API as API
    from pynrfjprog.Hex import Hex
except ImportError:
    print("Error: Could not find pynrfjprog.\nHave you run `pip install pynrfjprog`?")
    exit(1)


def connect(snr=None, jlink_khz=50000):
    nrf = NrfAPI(NrfDeviceFamily.NRF51)
    nrf.open()
    if snr:
        nrf.connect_to_emu_with_snr(snr, jlink_khz)
    else:
        nrf.connect_to_emu_without_snr(jlink_khz)
    try:
        device_version = nrf.read_device_version()
    except API.APIError as e:
        if e.err_code == API.NrfjprogdllErr.WRONG_FAMILY_FOR_DEVICE:
            nrf.close()
            nrf = NrfAPI(NrfDeviceFamily.NRF52)
            nrf.open()
            if snr:
                nrf.connect_to_emu_with_snr(snr, jlink_khz)
            else:
                nrf.connect_to_emu_without_snr(jlink_khz)
        else:
            raise e
    return nrf


def list_devices():
    nrf = NrfAPI(NrfDeviceFamily.NRF51)
    nrf.open()
    devices = nrf.enum_emu_snr()
    if devices:
        print("\n".join(list(map(str, devices))))
        nrf.close()


class RTT(object):
    """RTT commication class"""
    def __init__(self, nrf):
        self._nrf = nrf
        self._close_event = None
        self._writer_thread = None
        self._reader_thread = None

    def _writer(self):
        while not self._close_event.is_set():
            data = sys.stdin.readline().strip("\n")
            if len(data) > 0:
                self._nrf.rtt_write(0, data)
                # Yield
            time.sleep(0.1)

    def _reader(self):
        BLOCK_SIZE = 512
        rtt_data = ""
        while not self._close_event.is_set():
            try:
                rtt_data = self._nrf.rtt_read(0, BLOCK_SIZE)
            except Exception as e:
                continue

            if rtt_data == "" or type(rtt_data) == int:
                time.sleep(0.1)
                continue
            rtt_data = rtt_data.rstrip("\r\n")
            for s in rtt_data.splitlines():
                if s.strip() == "":
                    continue
                try:
                    sys.stdout.buffer.write(bytes(s, "ascii"))
                except Exception as e:
                    continue

                sys.stdout.buffer.write(b'\n')
                sys.stdout.buffer.flush()

    def run(self):
        self._nrf.rtt_start()

        # Wait for RTT to find control block etc.
        time.sleep(0.5)
        try:
            while not self._nrf.rtt_is_control_block_found():
                logging.info("Looking for RTT control block...")
                self._nrf.rtt_stop()
                time.sleep(0.5)
                self._nrf.rtt_start()
                time.sleep(0.5)
        except KeyboardInterrupt as e:
            return

        self._close_event = threading.Event()
        self._close_event.clear()
        self._reader_thread = threading.Thread(target=self._reader)
        self._reader_thread.start()
        self._writer_thread = threading.Thread(target=self._writer)
        self._writer_thread.start()

        try:
            while self._reader_thread.is_alive() or \
                  self._writer_thread.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt as e:
            self._close_event.set()
            self._reader_thread.join()
            self._writer_thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("pyrtt-viewer")
    parser.add_argument("-s", "--segger-id", help="SEGGER ID of the nRF device", type=int)
    args = parser.parse_args()
    nrf = connect(args.segger_id)
    rtt = RTT(nrf)
    rtt.run()
