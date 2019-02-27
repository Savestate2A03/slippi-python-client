import struct
from pubsub import pub

class GameDataProcessor:
    def __init__(self, wiiname):
        self.ready = False
        self.active = False
        self.wiiname = wiiname
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
            "ended": 0x00,
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
            "buttons": {
                "start": False,
                "y": False,
                "x": False,
                "b": False,
                "a": False,
                "l": False,
                "r": False,
                "z": False,
                "dU": False,
                "dD": False,
                "dL": False,
                "dR": False
            },
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
        self.info["followers"] = [
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
        chars = self.info["chars"] if (data[0x06] == 0) else self.info["followers"]
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
        buttons = data[0x31:0x31+2]
        player["buttons"] = {
            "start": ((data[0x31] >> 4 & 1) == 1),
            "y":     ((data[0x31] >> 3 & 1) == 1),
            "x":     ((data[0x31] >> 2 & 1) == 1),
            "b":     ((data[0x31] >> 1 & 1) == 1),
            "a":     ((data[0x31] >> 0 & 1) == 1),
            "l":     ((data[0x32] >> 6 & 1) == 1),
            "r":     ((data[0x32] >> 5 & 1) == 1),
            "z":     ((data[0x32] >> 4 & 1) == 1),
            "dU":    ((data[0x32] >> 3 & 1) == 1),
            "dD":    ((data[0x32] >> 2 & 1) == 1),
            "dL":    ((data[0x32] >> 1 & 1) == 1),
            "dR":    ((data[0x32] >> 0 & 1) == 1)
        }
        player["triggerL"] = struct.unpack('>f', data[0x33:0x33+4])[0]
        player["triggerR"] = struct.unpack('>f', data[0x37:0x37+4])[0]

    def postFrameProcess(self, data):
        chars = self.info["chars"] if (data[0x06] == 0) else self.info["followers"]
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

    def gameEndProcess(self, data):
        g = self.info["gameData"]
        g["ended"] = data[0x1]
