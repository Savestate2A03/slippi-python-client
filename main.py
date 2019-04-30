
import time 
from pubsub import pub
from SlippiPy import SlippiClient
import obswebsocket, obswebsocket.requests

obs = obswebsocket.obsws("localhost", 4444)
obs.connect()
obsItem = "obs websocket test item"

# note: Slippi-PercentChange isn't being published to yet
def onPercentChange(player, isFollower, oldPercent, newPercent):
    print(f"{'follower' if isFollower else 'player'} {player}: {oldPercent}% --> {newPercent}%")

def onGameInactive(wiiname):
    print(f"{wiiname}: Game Inactive")
    obs.call(obswebsocket.requests.SetSourceFilterSettings(obsItem, "Color Correction", {'opacity': 0}))
obsItem
def onGameActive(wiiname):
    print(f"{wiiname}: Game Active")
    obs.call(obswebsocket.requests.SetSourceFilterSettings(obsItem, "Color Correction", {'opacity': 100}))

def onMatchStatus(wiiname, status):
    print(f"{wiiname}: Match Status is {status}")

# listeners
pub.subscribe(onPercentChange, 'Slippi-PercentChange')
pub.subscribe(onGameInactive, 'Slippi-GameInactive')
pub.subscribe(onGameActive, 'Slippi-GameActive')
pub.subscribe(onMatchStatus, 'Slippi-MatchStatus')

# connect to wii and start relay server
slippi = SlippiClient()
slippi.addNewWii("wii", "localhost", port=671)

while True: 
    time.sleep(0.5)
    pass
