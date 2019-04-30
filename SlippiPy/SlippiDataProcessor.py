
import struct
import time
from enum import Enum
from pubsub import pub

class SlippiDataProcessor:

    def __init__(self, wiiname):
        self.info = self.getNewInfo()
        self.wiiname = wiiname
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
        self.ramfile = b''
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
                index += 5
                continue

            command = struct.unpack('B', data[index:index+1])[0]

            if (not gdp.active) and (not (self.CMD(command) == self.CMD.GAME_END)):
                gdp.active = True
                if ((self.CMD(command) != self.CMD.GAME_START) and (self.CMD(command) != self.CMD.COMMANDS)):
                    pub.sendMessage('Slippi-GameActive', wiiname=self.wiiname)
            
            if command not in self.info["payloadSizes"]:
                if command != 0x35:
                    return # started in the middle of a match ??
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
                pub.sendMessage('Slippi-MatchStatus', status=True, wiiname=self.wiiname)
                pub.sendMessage('Slippi-NewFile', wiiname=self.wiiname)
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
                pub.sendMessage('Slippi-MatchStatus', status=False, wiiname=self.wiiname)
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