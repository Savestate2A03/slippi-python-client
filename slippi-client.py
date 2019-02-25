import socket
import struct
import time
from enum import Enum

# Adapted the networking code from here:
# https://github.com/project-slippi/slippi-desktop-app/blob/master/app/domain/SlpFileWriter.js
# https://github.com/project-slippi/slippi-desktop-app/blob/master/app/domain/ConsoleConnection.js

class SlippiClient: 
    """For getting real-time data from slippi-enabled Wiis"""
    def __init__(self, ip, slippiProcessor, gameDataProcessor, port=666):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        i = 0
        while True:
            data = self.sock.recv(4096)
            slippiProcessor.handleData(data, gameDataProcessor)
            i += 1

class GameDataProcessor:
    def __init__(self):
        self.ready = False
        self.info = {}

    def newGame(self):
        return {
            "isTeams": False,
            "stage": 0x0000,
            "externalCharIDs": [0,0,0,0],
            "playerTypes": [0,0,0,0],
            "stockStartCount": [0,0,0,0],
            "characterColor": [0,0,0,0],
            "teamColor": [0,0,0,0],
            "randomSeed": 0x00000000,
            "ended": False
        }

    def newChar(self):
        return {
            "isFollower": False,
            "actionStateID": 0x0000,
            "internalCharId": 0x00,
            "percent": 0.000,
            "shieldSize": 0.000,
            "lastAttackLanded": 0x00,
            "currentComboCount": 0x00,
            "lastHitBy": 0x00,
            "stocks": 0x00,
            "actionStateFrameCounter": 0.000,
            "x": 0.000,
            "y": 0.000,
            "direction": 0.000,
            "joyX": 0.000,
            "joyY": 0.000,
            "cX": 0.000,
            "cY": 0.000,
            "buttons": 0x00000000,
            "triggerL": 0.000,
            "triggerR": 0.000,
        }

    def gameStartProcess(self, data):
        self.info["gameData"] = self.newGame()
        self.info["chars"] = [
            self.newChar(),
            self.newChar(),
            self.newChar(),
            self.newChar()
        ]
        g = self.info["gameData"]
        g["isTeams"] = True if (data[0x0D] == 1) else False 
        g["stage"] = struct.unpack('>H', data[0x13:0x13+2])[0]
        for i in range(4):
            g["externalCharIDs"][i] = data[0x65 + 0x24*i]
            g["playerTypes"][i]     = data[0x66 + 0x24*i]
            g["stockStartCount"][i] = data[0x67 + 0x24*i]
            g["characterColor"][i]  = data[0x68 + 0x24*i]
            g["teamColor"][i]       = data[0x6E + 0x24*i]
        g["randomSeed"] = struct.unpack('>I', data[0x13D:0x13D+4])[0]
        print(g)

    def preFrameProcess(self, data):
        chars = self.info["chars"]
        playerIndex = data[0x05]
        player = chars[playerIndex] 
        player["isFollower"] = True if (data[0x06] == 1) else False
        player["actionStateID"] = struct.unpack('>H', data[0xB:0xB+2])[0]
        player["x"] = struct.unpack('>f', data[0xD:0xD+4])[0]
        player["y"] = struct.unpack('>f', data[0x11:0x11+4])[0]
        player["direction"] = struct.unpack('>f', data[0x15:0x15+4])[0]
        player["joyX"] = struct.unpack('>f', data[0x19:0x19+4])[0]
        player["joyY"] = struct.unpack('>f', data[0x1D:0x1D+4])[0]
        player["cX"] = struct.unpack('>f', data[0x21:0x21+4])[0]
        player["cY"] = struct.unpack('>f', data[0x25:0x25+4])[0]
        player["buttons"] = struct.unpack('>H', data[0x31:0x31+2])[0]
        player["triggerL"] = struct.unpack('>f', data[0x33:0x33+4])[0]
        player["triggerR"] = struct.unpack('>f', data[0x37:0x37+4])[0]

    def postFrameProcess(self, data):
        chars = self.info["chars"]
        playerIndex = data[0x05]
        player = chars[playerIndex] 
        player["isFollower"] = True if (data[0x06] == 1) else False
        player["internalCharId"] = data[0x7]
        player["actionStateID"] = struct.unpack('>H', data[0x8:0x8+2])[0]
        player["x"] = struct.unpack('>f', data[0xA:0xA+4])[0]
        player["y"] = struct.unpack('>f', data[0xE:0xE+4])[0]
        player["direction"] = struct.unpack('>f', data[0x12:0x12+4])[0]
        player["percent"] = struct.unpack('>f', data[0x16:0x16+4])[0]
        player["shieldSize"] = struct.unpack('>f', data[0x1A:0x1A+4])[0]
        player["lastAttackLanded"] = data[0x1E]
        player["currentComboCount"] = data[0x1F]
        player["lastHitBy"] = data[0x20]
        player["stocks"] = data[0x21]
        player["actionStateFrameCounter"] = struct.unpack('>f', data[0x22:0x22+4])[0]
        self.ready = True # ok NOW you can get data
        print(self.info)

    def gameEndProcess(self, data):
        g = self.info["gameData"]
        g["ended"] = data[0x1]

class SlippiFileProcessor:

    def __init__(self):
        self.info = self.getNewInfo()
        self.ramfile = b''

    class CMD(Enum):
        COMMANDS          = 0x35
        GAME_START        = 0x36
        PRE_FRAME_UPDATE  = 0x37
        POST_FRAME_UPDATE = 0x38
        GAME_END          = 0x39

    def getNewInfo(self):
        return {
            "payloadSizes": {},
            "previousBuffer": b'',
            "bytesWritten": 0,
            "metadata": {
                "startTime": None,
                "lastFrame": 0,
                "players": {}
            }
        }

    def processRecvCommands(self, data):
        payloadLen = data[0]
        for i in range(1, payloadLen, 3):
            commandByte = data[i]
            payloadSize = struct.unpack('>H', data[i+1:i+3])[0]
            self.info["payloadSizes"][commandByte] = payloadSize
        return payloadLen

    def processCommand(self, command, data):
        payloadSize = self.info["payloadSizes"][command]

        if (command == self.CMD.POST_FRAME_UPDATE):
            # get info to update metadata fields
            frameIndex     = struct.unpack('I', data[0])[0]
            playerIndex    = struct.unpack('B', data[4])[0]
            isFollower     = struct.unpack('B', data[5])[0]
            internalCharId = struct.unpack('B', data[6])[0]

            # if not follower, process
            if (isFollower == 0):
                # update frame index
                self.info["metadata"]["lastFrame"] = frameIndex

                # update char usage
                prevPlayer = self.info["metadata"]["players"][playerIndex]
                prevPlayer["charUsage"][internalCharId] += 1

        return payloadSize

    def initNewGame(self):
        startTime = time.time()
        self.info = self.getNewInfo()
        self.info["metadata"]["startTime"] = startTime
        header = b'{U\x03raw[$U#1\x00\x00\x00\x00'
        self.ramfile += header
        print("Created new RAM file ...")

    def endGame(self):
        self.info["previousBuffer"] = b''
        pass #todo ??

    def writeCommand(self, command, payloadPtr, payloadLen):
        self.info["bytesWritten"] += (payloadLen + 1)
        self.ramfile += (bytes(command) + payloadPtr[:payloadLen])

    def handleData(self, newData, gdp):
        isNewGame = False
        isGameEnd = False
        # ----
        index = 0
        data = self.info["previousBuffer"] + newData
        while (index < len(data)):
            if(data[:5] == b'HELO\x00'):
                print("HELO")
                index += 5
                continue

            command = struct.unpack('B', data[index:index+1])[0]
            if command not in self.info["payloadSizes"]:
                payloadSize = 0
            else:
                payloadSize = self.info["payloadSizes"][command]
            remainingLen = len(data) - index
            if (remainingLen < payloadSize + 1):
                # if remaining length is not long enough for
                # full payload, save the remaining data until
                # we receive more data. The data has been split up.
                self.info["previousBuffer"] = data[index:];
                break

            # clear previous buffer here
            self.info["previousBuffer"] = b''

            # increment by one for the command byte
            index += 1; 

            # prepare to write payload
            payloadPtr = data[index:]
            payloadPtrWithCommand = data[index-1:]
            dataNoCommand = data[1:]
            payloadLen = 0

            # ugly ugly if elif elif elif etc
            if (self.CMD(command) == self.CMD.COMMANDS):
                isNewGame = True
                self.initNewGame()
                payloadLen = self.processRecvCommands(dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)
            elif (self.CMD(command) == self.CMD.GAME_END):
                payloadLen = self.processCommand(command, dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)
                self.endGame()
                gdp.gameEndProcess(payloadPtrWithCommand)
                isGameEnd = True
            elif (self.CMD(command) == self.CMD.GAME_START):
                payloadLen = self.processCommand(command, dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)
                gdp.gameStartProcess(payloadPtrWithCommand)
            elif (self.CMD(command) == self.CMD.PRE_FRAME_UPDATE):
                payloadLen = self.processCommand(command, dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)
                gdp.preFrameProcess(payloadPtrWithCommand)
            elif (self.CMD(command) == self.CMD.POST_FRAME_UPDATE):
                payloadLen = self.processCommand(command, dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)
                gdp.postFrameProcess(payloadPtrWithCommand)
            else:
                payloadLen = self.processCommand(command, dataNoCommand)
                self.writeCommand(command, payloadPtr, payloadLen)

            index += payloadLen

        # give to the caller
        return {
            "isNewGame": isNewGame,
            "isGameEnd": isGameEnd
        }

slippi_process = SlippiFileProcessor()
gdp = GameDataProcessor()
slippi = SlippiClient("10.5.0.16", slippi_process, gdp)

