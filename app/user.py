#import

class User:

	def __init__(self, socket, id):
		self.id = id # unique id
		self.place = None # place on the board
		self.name = "1"
		self.role = "spectator"
		self.socket = socket
		self.disconnected = False
		self.session = None # mostly for verifying a person if they need to reconnect
		self.teamLeader = False
		self.teamMember = False
		self.voteAffirmative = None

	def isGood(self):
		if self.role == 'good' or self.role == 'nilrem':
			return True
		else:
			return False