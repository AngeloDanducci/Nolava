#import

class User:

	def __init__(self, socket):
		self.id = 1
		self.name = None
		self.role = None
		self.socket = socket
		self.session = None
