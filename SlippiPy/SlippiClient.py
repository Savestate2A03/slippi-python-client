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
        self.clients = []
        self.wiis = {}
        self.newClientLock = threading.Lock()
        self.clientLock = threading.Lock()

        # increments every time a client connects
        # currently used for name. will add the ability
        # to rename clients later or something. 
        self.clientNumber = 0 

        # this thread listens out for slippi launcher clients
        # currently implemented to be 16 at most at one time
        _thread.start_new_thread(self.clientConnectThread,())

        # Slippi-RelayData is published to when a Wii sends
        # data to SlippiPy. It then relays the data to the
        # appopriate clients.
        pub.subscribe(self.handleClients, 'Slippi-RelayData') 

        # Clients start off unactivated. When they're not active,
        # then the heloZone (below) picks them up and sends them
        # HELOs to keep them connected. 
        pub.subscribe(self.activateClient, 'Slippi-NewFile')

        # Match status is needed in the event a Wii is removed
        # or a Clients attached Wii is changed. If a match is ongoing,
        # a disconnect match command is sent. 
        pub.subscribe(self.setMatchStatus, 'Slippi-MatchStatus')

        # Clients are attached and detached to wiis through
        # he subscriber / publisher model
        pub.subscribe(self.attachClientToWii, 'Slippi-AttachClientToWii')

        # helo zone, for connections waiting 
        # to be marked to recieve data
        _thread.start_new_thread(self.heloZoneThread,())

    def addNewWii(self, wiiname, ip, port=666):
        if wiiname not in self.wiis.keys():
            # set up a wii for recieving data
            _thread.start_new_thread(self.wiiConnectThread,(wiiname, ip, port))
        else:
            print(f'name "{wiiname}" already exists!')

    def removeWii(self, wiiname):
        # setting it inactive will automatically  
        # disconnect it in the wiiConnectThread
        self.wiis[wiiname]["active"] = False

    def clientConnectThread(self):
        print("Client connect thread ...")
        # connect to slippi clients
        relay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        relay.bind(('0.0.0.0', 666)) # allow connections from anywhere
        relay.listen(16) # max 16 clients for now ...
        while True:
            relaySock, relayAddr = relay.accept()
            self.onNewClient(relaySock, relayAddr) # add to clients list

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
            pub.sendMessage('Slippi-RelayData', data=data, wiiname=wiiname)

        print(f"Wii {wiiname} not active anymore")

        # send all connected clients a game end message if needed,
        # then mark as not ready for data
        with self.clientLock:
            for client in self.clientsFromWiiName(wiiname):
                if client["midgame"]:
                    print(f'Sending client "{client["name"]}" endgame data')
                    self.sendClientDataAndCheck(client, b'\x39\x00') # inconclusive end
                client["wiiname"] = None
                client["midgame"] = False
                client["sendData"] = False
                # gets put into the helo zone

        sock.close()
        self.wiis.pop(wiiname) # remove wii from wii dict

        print(f'Disconnected from wii "{wiiname}" @ {ip}')

    def heloZoneThread(self):
        print("Helo zone thread ...")
        while True:
            time.sleep(3)
            with self.clientLock:
                [self.sendHelo(client) for client in self.clients if not client["sendData"]]

    # lock before use
    def sendHelo(self, client):
        if not client["sendData"]: # hasn't been around long
                                   # enough to see a game start
            print(f'Sending b\'HELO\\x00\' to client "{client["name"]}"')
            self.sendClientDataAndCheck(client, b'HELO\x00')

    def onNewClient(self, sock, addr):
        with self.newClientLock:
            newClient = {
                "name": f"client{self.clientNumber}",
                "sock": sock,
                "wiiname": None,
                "midgame": False,
                "sendData": False
            }
            self.clientNumber += 1
        with self.clientLock:
            self.clients.append(newClient)
        print(f'New client "{newClient["name"]}": {addr}')

    def attachClientToWii(self, name, wiiname):
        with self.clientLock:
            client = self.clientFromName(name)
            if client == None: 
                return # no client with name {name}
            if client["wiiname"] == wiiname:
                return # already attached
            if client["midgame"]:
                print(f'Sending client "{client["name"]}" endgame data')
                self.sendClientDataAndCheck(client, b'\x39\x00') # inconclusive end
            client["wiiname"] = wiiname 
            client["midgame"] = False
            client["sendData"] = False # helo zone
            print(f'Attached client "{client["name"]}" to Wii "{wiiname}"')

    # for each client attached to {wiiname}, relay data if ready to recieve
    def handleClients(self, data, wiiname):
        with self.clientLock:
            [self.sendClientData(client, data) for client in self.clientsFromWiiName(wiiname) if client["sendData"]]

    # mark client ready to recieve relayed data
    def activateClient(self, wiiname):
        with self.clientLock:
            for client in self.clientsFromWiiName(wiiname):
                if not client["sendData"]:
                    print(f'Enabled Wii data for client "{client}"')
                    client["sendData"] = True

    # mark in-game or not for each client attached to a wii 
    def setMatchStatus(self, wiiname, status):
        with self.clientLock:
            for client in self.clientsFromWiiName(wiiname):
                client["midgame"] = status
                print(f'"{client["name"]}": Match status now {status}')

    # lock before use
    def sendClientData(self, client, data): 
        # wrapper for sendClientDataAndCheck that also
        # checks if client is ready to recieve data
        if client["sendData"]:
            self.sendClientDataAndCheck(client, data)

    # lock before use
    def sendClientDataAndCheck(self, client, data):
        try:
            client["sock"].sendall(data)
        except ConnectionAbortedError:
            # if client ran off, remove them from the list
            client["sock"].close()
            print(f'Closed client "{client["name"]}"')
            self.clients = [c for c in self.clients if c["sock"] != client["sock"]]

    # lock before use
    def clientsFromWiiName(self, wiiname):
        return [client for client in self.clients if client["wiiname"] == wiiname]

    # lock before use
    def clientFromName(self, name):
        for client in self.clients:
            if client["name"] == name:
                return client
        return None