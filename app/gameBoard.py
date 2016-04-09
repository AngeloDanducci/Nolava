#import

class GameBoard:

	def __init__(self, numPlayers):
		self.numPlayers = numPlayers
		self.questSuccesses = 0
		self.questFails = 0
		self.attemptedTeams = 1
		self.accepts = 0
		self.rejects = 0
		self.fails = 0
		self.questNumber = 1

	def playersOnTeam(self):
		if (self.questNumber == 1):
			if (self.numPlayers == 5):
				return 2
		elif (self.questNumber == 2):
			if (self.numPlayers == 5):
				return 3
		elif (self.questNumber == 2):
			if (self.numPlayers == 5):
				return 2
		elif (self.questNumber == 2):
			if (self.numPlayers == 5):
				return 3
		elif (self.questNumber == 2):
			if (self.numPlayers == 5):
				return 3
