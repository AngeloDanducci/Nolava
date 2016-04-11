#!/usr/bin/python3

import time
import random
import uuid
import html
import re
from wsocket import WSocket
from user import User
from gameBoard import GameBoard

# empty string here for all available interfaces, same as socket, 0 for timeout
ws = WSocket('', 1400, 0)
allRoles = ['nilrem', 'nissassa', 'good', 'evil']
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
timerStart = None # DateTime
timerLength = 60 # seconds
leaderPlace = 0
users = []
disconnected = []
sessions = {}
roles = {'nilrem':None, 'nissassa':None, 'good':[], 'evil':[]}
gameState = None

def htmlEncode(text):
	return html.escape(text)

def initUser(user):
	# ask user their name
	# WSocket.send(user.socket, "request:name")
	pass

def joinGame(user):
	# Enforce max number of players
	usersPlaying = [x for x in users if x.role == None]

	if state == 'not_started':
		if len(usersPlaying) < 5:
			user.role = None
			for u in users:
				send(u, 'success:%s %s' % (user.name, ' has joined the game.'))
		else:
			send(user, 'error:%s' % ('The game already has the max number of players.'))
	else:
		send(user, 'error:%s' % ('Sorry, the game has already started.'))

def whoami(user):
	# Tell the user everything they should know based on what role they are (including score etc.)
	# This function should be used in two places, when a user reconnects, and when they
	# are first assigned a role
	print('whoami')
	send(user, 'state:%s' % (state))

	send(user, 'assign:%s' % (user.place))
	send(user, 'assign:%s' % (user.role))

	if user.role == 'nilrem':
		# Sees all evil players except derdrom
		notifyEvilPlayers(user, False)
	elif user.role == 'nissassa' or user in roles['evil']:
		notifyEvilPlayers(user, True)
	# elif user.role == 'lavicrep':
	# 	# Knows who Merlin is, (but Morgana is also shown as Merlin)
	# 	# use queue of messages to randomize the order
	# 	queue = []
	# 	if roles['anagrom'] != None:
	# 		queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'nilrem'))
	# 	if roles['nilrem'] != None:
	# 		queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'nilrem'))

	# 	random.shuffle(queue)
	# 	for msg in queue:
	# 		send(user, msg)
	# elif user.role == 'derdrom' or user.role == 'anagrom' or user in roles['evil']:
	# 	notifyEvilPlayers(user, True)

	# Finally, notify the user of all spots that are taken... Useful if the game is still joinable and whatnot
	for u in [x for x in users if x.place != None]:
		send(user, 'place:%s:%s' % (u.place, u.name))

	# TODO also show quest leader and score!


def notifyEvilPlayers(user, includeDerdrom):
	# In order to prevent the client from being like "Hey, the guy who's sent last is the assassin"
	# queue the messages in a list and randomize them...
	queue = []
	for u in roles['evil']:
		queue.append('place:%s:%s:%s' % (u.place, u.name, u.role))

	# if includeDerdrom and roles['derdrom'] != None:
	# 	queue.append('place:%s:%s:%s' % (roles['derdrom'].place, roles['derdrom'].name, 'derdrom'))

	# if roles['anagrom'] != None:
	# 	queue.append('place:%s:%s:%s' % (roles['anagrom'].place, roles['anagrom'].name, 'anagrom'))

	if roles['nissassa'] != None:
		queue.append('place:%s:%s:%s' % (roles['nissassa'].place, roles['nissassa'].name, 'evil'))

	random.shuffle(queue)
	for msg in queue:
		send(user, msg)


def send(user, data):
	try:
		WSocket.send(user.socket, data)
		return True
	except:
		# If we couldn't send data to a user, remove them from list of users,
		# add to disconnected list, and notify everyone else the user disconnected
		try:
			users.remove(user)
			# Save the user if they have a session (which means they are playing)
			if user.session != None:
				disconnected.append(user)
			for u in users:
				send(u, '%s:%s' % ('disconnected', user.name))

			return False
		except ValueError:
			# If the user is not users trying to remove it creates a value error.
			# catching the error is useful here to not spam users about a disconnect
			# and prevent unintended loops
			return False

def startGame():
	# Give all users an assigned place and role and start the first round
	# all users that have an assigned place
	global roles
	global gameState
	gameState = GameBoard(5)
	usersPlaying = [x for x in users if x.role == None]
	random.shuffle(usersPlaying)

	rolesLeft = list(allRoles)
	rolesLeft.append('good')

	place = 1

	while len(usersPlaying) > 0:
		role = random.choice(rolesLeft)
		rolesLeft.remove(role)

		user = usersPlaying.pop(0)
		user.session = uuid.uuid1()
		sessions[user.session] = user
		user.role = role
		user.place = place
		send(user, 'assign:%s' % (user.place))
		send(user, 'assign:%s' % (user.role))
		send(user, 'session:%s' % (user.session))

		place += 1
		if role == 'evil' or role == 'good':
			roles[role].append(user)
		else:
			roles[role] = user

	startRound()
	for user in users:
		whoami(user)

def numOrInf(x):
	if not x:
		return 99999999999
	else:
		return x

def startRound():
	# Assign new leader, start timer
	global leaderPlace
	global state

	for u in users:
		u.teamLeader = False
		u.teamMember = False
		u.voteAffirmative = None

	leaderPlace = (leaderPlace + 1) % gameState.numPlayers

	newLeader = None
	for user in users:
		if user.place == leaderPlace:
			newLeader = user

	newLeader.teamLeader = True
	send(newLeader, 'quest:leader')

	for user in users:
		send(user, 'leader:%s' % (leaderPlace))
		# Tell everyone how many players to be on team
		send(user, 'members_needed:%s' % (gameState.playersOnTeam()))

	state = 'choose_team'
	startTimer()

def gameAction(action):
	# Does specific things for the game as a whole, such as starting it
	if action == 'start' and state == 'not_started':
		startGame()
	#elif action == 'pause':

def startTimer():
	global timerStart
	timerStart = time.time()
	for user in users:
		send(user, 'timer:%s' % (timerLength))

def missionSuccess(x):
	for user in users:
		send(user, 'missionSuccess:%s', gameState.questNumber)

def missionFail(x):
	for user in users:
		send(user, 'missionFail:%s', gameState.questNumber)

def questNoGo(x):
	for user in users:
		send(user, 'questNoGo:%s', gameState.attemptedTeams)

def roundTimeIsUp():
	# Check if the time has elapsed and update data structures
	global timerStart
	if timerStart != None:
		if time.time() > timerStart + timerLength:
			timerStart = None
			return True
	return False

def stateSatisfied():
	global state
	# TODO: Did one team win?

	if state == 'choose_team':
		playersNeeded = gameState.playersOnTeam()
		currentPlayers = 0
		teamMembers = [x for x in users if x.teamMember == True]
		currentPlayers += len(teamMembers)

		if currentPlayers == playersNeeded:
			# Advance to next game state
			state = 'vote_quest'
			for user in users:
				send(user, 'success:%s' % ('Team voting has begun'))
				for u in teamMembers:
					send(user, 'team_member:%s' % (u.place))
			startTimer()

	elif state == 'vote_quest':
		# TODO did team members all vote to accept/reject team?
		votes = 0
		players = [x for x in users if x.role != 'spectator']
		for user in players:
			if user.voteAffirmative != None:
				votes += 1

		if votes == len(players):
			# Tell everyone who voted what
			fails = 0
			for user in users:
				send(user, 'success:%s voted %s.' % (user.name, user.voteAffirmative))
				if not user.voteAffirmative:
					fails += 1

			if fails / len(players) >= .5:
				#increement attemptedTeams
				gameState.attemptedTeams += 1
				# If there have been 5 failures to go on the quest,
				# then the quest fails
				if gameState.attemptedTeams >= 5:
					questNoGo(gameState.attemptedTeams)
					#hide party counter 5, show party counter 1
					gameState.attemptedTeams = 1
					missionFail(gameState.questNumber)
					gameState.questOutcomes[gameState.questNumber-1] = 'evil'
					gameState.questNumber += 1
				#show correct party counter
				questNoGo(gameState.attemptedTeams)
				startRound()
			else:
				state = 'quest_success_or_fail'

	elif state == 'quest_success_or_fail':
		votesNeeded = gameState.playersOnTeam()
		votes = 0
		teamMembers = [x for x in users if x.teamMember == True or x.teamLeader == True]
		for user in teamMembers:
			if user.voteAffirmative != None:
				votes += 1

		if votes == votesNeeded:
			success = True
			for user in teamMembers:
				if user.voteAffirmative == False:
					success = False

			if success:
				#TO DO display @ quest number
				missionSuccess(gameState.questNumber)
				gameState.questOutcomes[gameState.questNumber-1] = 'good'
			else:
				#TO DO display @ quest number
				missionFail(gameState.questNumber)
				gameState.questOutcomes[gameState.questNumber-1] = 'evil'
			gameState.questNumber += 1

			if gameState.questOutcomes.count('good') == 3:
				state = 'assassinate'
				for user in users:
					send(user, 'state:assassinate')
			elif gameState.questOutcomes.count('evil') == 3:
				state = 'game_over'
				for user in users:
					send(user, 'evil_wins:true')
			else:
				startRound()

	elif state == 'assassinate':
		# TODO did assassin choose target?
		# Just pass here, when assassin chooses target the game state will advance
		# automatically because there is nothing to wait for
		pass
	elif state == 'not_started':
		# Just pass here, when game admin starts the game the state will advance
		# automatically because there is nothing to wait for after that
		return False

def doDefaultTimeOut():
	# TODO: Do whatever default actions shold be done here, the timer has elapsed
	global state
	if state == 'choose_team':
		# TODO: Pick team for leader randomly
		playersNeeded = gameState.playersOnTeam()
		onTeam = [x for x in users if x.teamMember == True]
		notOnTeam = [x for x in users if x.role != 'spectator']
		random.shuffle(notOnTeam)

		while len(onTeam) < playersNeeded:
			x = notOnTeam.pop
			x.teamMember
			onTeam.append(x)
			# trying to fix an issue with u.TeamMember
		#for u in onTeam:
		#	u.teamMember = True
		state = 'vote_quest'
	elif state == 'vote_quest':
		voter = [x for x in users if x.role != 'spectator']
		for u in voter:
			if u.role == 'good' or u.role == 'nilrem':
				u.voteAffirmative = True
			else:
				u.voteAffirmative = True
	elif state == 'quest_success_or_fail':
		onTeam = [x for x in users if x.teamMember == True]
		for u in onTeam:
			if u.role == 'good' or u.role == 'nilrem':
				u.voteAffirmative = True
			else:
				u.voteAffirmative = False

def assassinVote(user, place):
	if user.role == 'nissassa' and state == 'assassinate':
		merlinFound = False
		if roles['nilrem'].place == place:
			merlinFound = True

		if merlinFound:
			for u in users:
				send(u, 'win:evil')
		else:
			for u in users:
				send(u, 'win:good')

def addToTeam(user, place):
	playersOnTeam = [x for x in users if x.teamMember == True]
	maxPlayers = gameState.playersOnTeam()

	if user.teamLeader and len(playersOnTeam) < maxPlayers:
		for u in users:
			if u.place == int(place):
				u.teamMember = True
				send(u, 'team:member')

try:
	userId = 1
	while True:
		if roundTimeIsUp():
			doDefaultTimeOut()

		stateSatisfied()

		client = ws.accept()
		if client is not None:
			# figure out who they are and add to list
			user = User(client, userId)
			userId = userId + 1
			initUser(user)
			users.append(user)

		# For each client, see if they sent anything
		for user in users:
			recvd = WSocket.recv(user.socket, 4096)
			if recvd is None:
				continue

			# If they did send something, send it to every client
			# THIS IS THE POINT WHERE WE WILL BE INSPECTING USER INPUT
			# TO SEE IF IT'S A CHAT MESSAGE, AN ATTEMPT AT MAKING A GAME
			# MOVE/VOTE/WHATEVER. IN THE CASE OF A MESSAGE, IT WILL
			# BE SENT TO EVERYONE

			# first, get action (should seperate into ['action', 'value'])
			action = recvd.decode('utf-8').split(':', 1)

			if action[0] == 'chat':
				for u in users:
					send(u, 'chat:%s:%s' % (htmlEncode(user.name), htmlEncode(action[1])))
			elif action[0] == 'name':
				# When someone updates their name, tell everyone
				# Could potentially be abused? TODO: rate limit? only allow once?
				# Check for duplicate name?
				regex = r'(\w+).*'
				match = re.match(regex, action[1])
				if match:
					user.name = match.group(1)
					for u in users:
						send(u, '%s:%s' % (user.id, htmlEncode(user.name)))
				pass
			elif action[0] == 'game':
				gameAction(action[1])
			elif action[0] == 'assassinate':
				assassinVote(user, action[1])
			elif action[0] == 'quester':
				addToTeam(user, action[1])
			elif action[0] == 'session':
				# If user is trying to reconnect, make sure they are given the correct user object
				sessionId = action[1]
				if sessionId in sessions:
					print('Tracked user reconnected.')
					sessions[sessionId] = user
					if user in disconnected:
						disconnected.remove(user)
						users.append(user)
				else:
					print('Untracked user connected with sessionId = %s' % (sessionId))
			elif action[0] == 'vote':
				# Should be either reject/approve or success/fail depending on what vote is for
				if user.teamMember:
					if action[1] == 'yes':
						user.voteAffirmative = True
					else:
						user.voteAffirmative = False
			elif action[0] == 'join':
				joinGame(user)
			elif action[0] == 'whoami':
				# If the client reconnects, the browser won't "remember" who is who
				# so remind them
				whoami(user)
except KeyboardInterrupt:
	print('\nKeyboardInterrupt.\nCleaning up and exiting')
	for user in users:
		user.socket.close()
	ws.close()
