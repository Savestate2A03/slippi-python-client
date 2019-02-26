from pubsub import pub
from SlippiPy import SlippiClient

def onPercentChange(player, isFollower, oldPercent, newPercent):
	print(f"{'follower' if isFollower else 'player'} {player}: {oldPercent}% --> {newPercent}%")

def onGameInactive():
	print("Game Inactive")

def onGameActive():
	print("Game Active")

# listeners
pub.subscribe(onPercentChange, 'Slippi-PercentChange')
pub.subscribe(onGameInactive, 'Slippi-GameInactive')
pub.subscribe(onGameActive, 'Slippi-GameActive')

# connect to wii and start relay server
slippi = SlippiClient.SlippiClient("10.5.0.16")