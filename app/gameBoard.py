#import

class GameBoard:

	def __init__(self, numPlayers):
		self.numPlayers = numPlayers
		self.questOutcomes = [None, None, None, None, None]
		self.attemptedTeams = 1
		self.fails = 0
		self.questNumber = 1

	def playersOnTeam(self):
		if (self.questNumber == 1):
			if (self.numPlayers == 5):
				return 2
		elif (self.questNumber == 2):
			if (self.numPlayers == 5):
				return 3
		elif (self.questNumber == 3):
			if (self.numPlayers == 5):
				return 2
		elif (self.questNumber == 4):
			if (self.numPlayers == 5):
				return 3
		elif (self.questNumber == 5):
			if (self.numPlayers == 5):
				return 3
		else:
			raise ValueError('Combination not account for: questNumber:%s, numPlayers:%s'
				% (self.questNumber, self.numPlayers))
