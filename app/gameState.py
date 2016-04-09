#import

class GameState:

	def __init__(numPlayers):
		self.numPlayers = numPlayers
        self.questSuccesses = 0;
        self.questFails = 0;
        self.attemptedTeams = 1;
        self.accepts = 0;
        self.rejects = 0;
        self.fails = 0;
        self.questNumber = 1;
