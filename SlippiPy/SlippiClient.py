import socket
import _thread
import asyncio
import time
from pubsub import pub

from . import GameDataProcessor
from . import SlippiDataProcessor

class SlippiClient: 
    """For getting real-time data from slippi-enabled Wiis"""
    def __init__(self, ip, port=666):
        # connect to wii
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1) # 100ms timeout
        sock.connect((ip, port))
        _thread.start_new_thread(self.onWiiConnect,(sock,))

        # connect to slippi
        self.clients = []
        relay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        relay.bind(('0.0.0.0', 666))
        relay.listen(16) # max 16 clients for now ...
        pub.subscribe(self.handleClients, 'Slippi-RelayData')
        pub.subscribe(self.configureNewClients, 'Slippi-NewFile')

        # helo generator
        _thread.start_new_thread(self.heloGenerator,())

        while True:
            relaySock, relayAddr = relay.accept()
            self.onNewClient(relaySock, relayAddr)

    def onNewClient(self, sock, addr):
        print(f'New client detected: {addr}')
        self.clients.append({
            "sock": sock,
            "sendData": False
        })

    def onWiiConnect(self, sock):
        print(f'Starting Wii connection thread ...')
        gdp = GameDataProcessor.GameDataProcessor()
        slp = SlippiDataProcessor.SlippiDataProcessor()
        while True:
            try:
                data = sock.recv(65536)
            except socket.timeout:
                if gdp.active:
                    gdp.active = False
                    pub.sendMessage('Slippi-GameInactive')
                continue
            slp.handleData(data, gdp)
            pub.sendMessage('Slippi-RelayData', data=data)

    def handleClients(self, data=None):
        if data != None:
            [self.sendClientData(client, data) for client in self.clients if client["sendData"]]

    def configureNewClients(self):
        for client in self.clients:
            if not client["sendData"]:
                print(f"Enabled connection for client {client}")
                client["sendData"] = True

    def sendClientData(self, client, data):
        if client["sendData"]:
            try:
                client["sock"].sendall(data)
            except ConnectionAbortedError:
                client["sock"].close()
                print(f"closed: {client}")
                self.clients = [c for c in self.clients if c["sock"] != client["sock"]]

    def heloGenerator(self):
        while True:
            time.sleep(3)
            [self.sendHelo(client) for client in self.clients if not client["sendData"]]

    def sendHelo(self, client):
        if not client["sendData"]: # hasn't been around long
                                   # enough to see a game start
            try:
                client["sock"].sendall(b'HELO\x00')
                print(f"sent helo to: {client}")
            except ConnectionAbortedError:
                client["sock"].close()
                print(f"closed: {client}")
                self.clients = [c for c in self.clients if c["sock"] != client["sock"]]

# slippiProcessor, gameDataProcessor

#        slippiReplayLauncher = self.relay.accept()
#        relaySocket = slippiReplayLauncher[0]
#        relayAddress = slippiReplayLauncher[1]
#        # connect to wii
#        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        self.sock.settimeout(0.1) # 100ms timeout
#        self.sock.connect((ip, port))
#        while True:
#            try:
#                data = self.sock.recv(4096) 
#            except socket.timeout:
#                if gameDataProcessor.active:
#                    gameDataProcessor.active = False
#                    print("Game not active")
#                    OBSInteract.hideSlippi()
#                continue
#            relaySocket.sendall(data)
#            slippiProcessor.handleData(data, gameDataProcessor)