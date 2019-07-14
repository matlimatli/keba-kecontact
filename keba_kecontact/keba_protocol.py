#!/usr/bin/python3

import asyncio
import logging
import json

_LOGGER = logging.getLogger(__name__)


class KebaProtocol(asyncio.DatagramProtocol):
    """Representation of a KEBA charging station connection protocol."""

    data = {}

    def __init__(self, callback):
        self._transport = None
        self._callback = callback

    def connection_made(self, transport):
        """Request base information after initial connection created."""
        self._transport = transport
        _LOGGER.debug("Asyncio UDP connection setup complete.")

    def error_received(self, exc):
        """Log error after receiving."""
        _LOGGER.error("Error received: %s", exc)

    def connection_lost(self, exc):
        """Set state offline if connection is lost."""
        _LOGGER.error("Connection lost.")
        self.data['Online'] = False

    def datagram_received(self, data, addr):
        """Handle received datagrams."""
        _LOGGER.debug("Data received.")
        self.data['Online'] = True
        decoded_data = data.decode()

        if 'TCH-OK :done' in decoded_data:
            _LOGGER.debug("Command accepted: %s", decoded_data)
            return True

        if 'TCH-ERROR' in decoded_data:
            _LOGGER.warning("Command rejected: %s", decoded_data)
            return False

        json_rcv = json.loads(data.decode())

        # Prepare received data
        if 'ID' in json_rcv:
            if json_rcv['ID'] == '1':
                try:
                    # Extract product version
                    product_string = json_rcv['Product']
                    if "P30" in product_string:
                        json_rcv['Product'] = "KEBA P30"
                    elif "P20" in product_string:
                        json_rcv['Product'] = "KEBA P20"
                    elif "BMW" in product_string:
                        json_rcv['Product'] = "BMW Wallbox"
                except KeyError:
                    _LOGGER.warning("Could not extract report 1 data for KEBA "
                                    "charging station")
            elif json_rcv['ID'] == '2':
                try:
                    json_rcv['Max curr'] = json_rcv['Max curr'] / 1000.0
                    json_rcv['Curr HW'] = json_rcv['Curr HW'] / 1000.0
                    json_rcv['Curr user'] = json_rcv['Curr user'] / 1000.0
                    json_rcv['Curr FS'] = json_rcv['Curr FS'] / 1000.0
                    json_rcv['Curr timer'] = json_rcv['Curr timer'] / 1000.0
                    json_rcv['Setenergy'] = round(
                        json_rcv['Setenergy'] / 10000.0, 2)
                except KeyError:
                    _LOGGER.warning("Could not extract report 2 data for KEBA "
                                    "charging station")
            elif json_rcv['ID'] == '3':
                try:
                    json_rcv['I1'] = json_rcv['I1'] / 1000.0
                    json_rcv['I2'] = json_rcv['I2'] / 1000.0
                    json_rcv['I3'] = json_rcv['I3'] / 1000.0
                    json_rcv['P'] = round(json_rcv['P'] / 1000000.0, 2)
                    json_rcv['PF'] = json_rcv['PF'] / 1000.0
                    json_rcv['E pres'] = round(json_rcv['E pres'] / 10000.0, 2)
                    json_rcv['E total'] = int(json_rcv['E total'] / 10000)
                except KeyError:
                    _LOGGER.warning("Could not extract report 3 data for KEBA "
                                    "charging station")
        else:
            _LOGGER.debug("No ID in response from Keba charging station")
            return False

        # Join data to internal data store and send it to the callback function
        self.data.update(json_rcv)
        self._callback(self.data)

    async def send(self, payload):
        """Send data to KEBA charging station."""
        _LOGGER.debug("Send %s", payload)
        self._transport.sendto(payload.encode())