import socket
import _thread
import asyncio
import time
from pubsub import pub
import threading

from . import GameDataProcessor
from . import SlippiDataProcessor

class SlippiClient: 
    """For getting real-time data from slippi-enabled Wiis"""
    def __init__(self, port=666):
        # init 
        self.wiis = {}

    def addNewWii(self, wiiname, ip, port=666):
        if wiiname not in self.wiis:
            # set up a wii for recieving data
            _thread.start_new_thread(self.wiiConnectThread,(wiiname, ip, port))
        else:
            print(f'name "{wiiname}" already exists!')

    def removeWii(self, wiiname):
        # setting it inactive will automatically  
        # disconnect it in the wiiConnectThread
        self.wiis[wiiname]["active"] = False

    def wiiConnectThread(self, wiiname, ip, port):
        print(f'Wii connection thread ...')

        # connect to wii
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2) # 2s timeout
            sock.connect((ip, port))
        except socket.timeout:
            print(f"Wii not found @ {ip}:{port}")
            return

        self.wiis[wiiname] = {}
        self.wiis[wiiname]["active"] = True

        gdp = GameDataProcessor.GameDataProcessor(wiiname)
        slp = SlippiDataProcessor.SlippiDataProcessor(wiiname)
        sock.settimeout(0.1) # 100ms timeout for switching
                             # to game feed source (usually)

        print(f'Added Wii "{wiiname}" @ {ip}:{port}')
        while self.wiis[wiiname]["active"]:
            try:
                data = sock.recv(65536)
            except socket.timeout:
                if gdp.active:
                    gdp.active = False
                    # subscribe to Slippi-GameInactive for your
                    # source switching needs
                    pub.sendMessage('Slippi-GameInactive', wiiname=wiiname)
                continue
            slp.handleData(data, gdp)

        print(f"Wii {wiiname} not active anymore")

        # send all connected clients a game end message if needed,
        # then mark as not ready for data

        sock.close()
        self.wiis.pop(wiiname) # remove wii from wii dict

        print(f'Disconnected from wii "{wiiname}" @ {ip}')