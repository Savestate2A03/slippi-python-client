import time 
from pubsub import pub
from SlippiPy import SlippiClient

# note: Slippi-PercentChange isn't being published to yet
def onPercentChange(player, isFollower, oldPercent, newPercent):
    print(f"{'follower' if isFollower else 'player'} {player}: {oldPercent}% --> {newPercent}%")

def onGameInactive(wiiname):
    print(f"{wiiname}: Game Inactive")

def onGameActive(wiiname):
    print(f"{wiiname}: Game Active")

def onMatchStatus(wiiname, status):
    print(f"{wiiname}: Match Status is {status}")

# listeners
pub.subscribe(onPercentChange, 'Slippi-PercentChange')
pub.subscribe(onGameInactive, 'Slippi-GameInactive')
pub.subscribe(onGameActive, 'Slippi-GameActive')
pub.subscribe(onMatchStatus, 'Slippi-MatchStatus')

# connect to wii and start relay server
slippi = SlippiClient.SlippiClient()
slippi.addNewWii("leftWii", "10.5.0.16")
slippi.addNewWii("rightWii", "10.5.0.18")

# the config read stuff is only temp
# when fully implemented, it'd be controlled
# by a UI of sorts, prob thru django
while True:
    time.sleep(0.5)
    clients = {}
    with open("config.txt") as config:
        for line in config:
            name, var = line.partition("=")[::2]
            clients[name.strip()] = var.strip()
    for client in clients:
        pub.sendMessage('Slippi-AttachClientToWii', name=client, wiiname=clients[client])