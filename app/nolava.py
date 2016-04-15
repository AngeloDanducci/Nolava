#!/usr/bin/python3

import time
import random
import uuid
import html
import re
from wsocket import WSocket
from user import User
from gameBoard import GameBoard

# GAME SETTINGS
timerLength = 60 # seconds
minPlayers = 5
maxPlayers = 5

# empty string here for all available interfaces, same as socket, 0 for timeout
ws = WSocket('', 1400, 0)
allRoles = ['nilrem', 'nissassa', 'good', 'evil']
stateList = ['not_started', 'choose_team', 'vote_quest', 'quest_success_or_fail', 'assassinate']
state = 'not_started'
timerStart = None # DateTime
leaderPlace = 0 # The place of the current leader
users = [] # all users, including spectators and disconnected users
players = [] # where index+1 is the users place on the board
roles = {'nilrem':None, 'nissassa':None, 'good':[], 'evil':[]}
sessions = {} # dictionary to select users by session
gameState = None

def htmlEncode(text):
	return html.escape(text)

def joinGame(user):
	# Enforce max number of players
	usersPlaying = [x for x in users if x.role == None]

	if state == 'not_started':
		if len(usersPlaying) < maxPlayers:
			if user.role != None:
				user.role = None
				sendAll(users, 'success:%s %s' % (user.name, ' has joined the game.'))
			else:
				send(user, 'success:You are already queued.')
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
	elif not user.isGood():
		# All evil players know who evil players are (but not their role!)
		notifyEvilPlayers(user, True)
	# elif user.role == 'lavicrep':
	# 	# Knows who Merlin is, (but Morgana is also shown as Merlin)
	# 	# use queue of messages to randomize the order

	# Give players place & name and show quest leader/members
	for p in players:
		send(user, 'place:%s:%s' % (p.place, p.name))
		if p.teamLeader:
			send(user, 'leader:%s' % (p.place))
		if p.teamMember:
			send(user, 'team_member:%s' % (p.place))

	# Show score
	for i in range(len(gameState.questOutcomes)):
		if gameState.questOutcomes[i] == 'good':
			send(user, 'mission_success:%s' % (i))
		elif gameState.questOutcomes[i] == 'evil':
			send(user, 'mission_fail:%s' % (i))

	send(user, 'quest_no_go:%s' % (gameState.attemptedTeams))


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

def sendAll(listUsers, data):
	for user in listUsers:
		send(user, data)

def send(user, data):
	try:
		if not user.disconnected and user.socket != None:
			WSocket.send(user.socket, data)
			return True
		else:
			return False
	except:
		# If we couldn't send data to a user, update the user object to show they
		# are disconnected and notify everyone of the disconnect
		user.disconnected = True
		for u in users:
			send(u, '%s:%s' % ('disconnected', user.name))

		return False

def reconnectUser(user, sessionId):
	# If user is trying to reconnect, make sure they are given the correct user object
	if sessionId in sessions:
		print('Tracked user reconnected.')
		sessions[sessionId].socket = user.socket
		sessions[sessionId].disconnected = False
		users.remove(user)
	else:
		print('Untracked user connected with sessionId = %s' % (sessionId))

def resetVotes():
	for user in players:
		user.voteAffirmative = None

def startGame(user):
	# Give all users an assigned place and role and start the first round
	# all users that have an assigned place
	global players
	global roles
	global gameState
	usersPlaying = [x for x in users if x.role == None]

	if len(usersPlaying) < minPlayers:
		send(user, 'error:Not enough players to start game, need at least %s.' % (minPlayers))

	gameState = GameBoard(len(usersPlaying))
	random.shuffle(usersPlaying)

	rolesLeft = list(allRoles)

	# Right here we should figure out how many extra evil/good players to add
	# or unique roles to remove if there are not enough
	if len(usersPlaying) == 5:
		# 2 evil players
		rolesLeft.append('good')
		# add regular good player or lavicrep ?
		# Keeping nissassa with 5 players basically makes a 1in3 chance evil wins anyway
		#rolesLeft.remove('nissassa')
		#rolesLeft.remove('derdrom')
		#rolesLeft.remove('anagrom')
		#rolesLeft.remove('norebo')
		# etc.
	#elif len(usersPlaying) == 6:
		# 2 evil players
	#elif len(usersPlaying) == 7:
		# 3 evil players
	#elif len(usersPlaying) == 8:
		# 3 evil players
	#elif len(usersPlaying) == 9:
		# 3 evil players
	#elif len(usersPlaying) == 10:
		# 4 evil players

	place = 1

	while len(usersPlaying) > 0:
		role = random.choice(rolesLeft)
		rolesLeft.remove(role)

		user = usersPlaying.pop(0)
		user.session = uuid.uuid1()
		user.role = role
		user.place = place
		sessions[user.session] = user
		players.append(user)
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

def startRound():
	# Assign new leader, start timer
	global leaderPlace
	global state

	for u in users:
		send(u, 'state:choose_team')

	for p in players:
		p.teamLeader = False
		p.teamMember = False
		p.voteAffirmative = None

	leaderPlace = (leaderPlace % gameState.numPlayers) + 1

	players[leaderPlace-1].teamLeader = True

	players[leaderPlace-1].teamLeader = True
	send(players[leaderPlace-1], 'quest:leader')

	for user in users:
		send(user, 'success:Quest leader chosen.')
		send(user, 'leader:%s' % (leaderPlace))

	print('Leader chosen, team choosing starting')
	state = 'choose_team'
	startTimer()

def gameAction(user, action):
	# Does specific things for the game as a whole, such as starting it
	if action == 'start' and state == 'not_started':
		startGame(user)
	#elif action == 'pause':

def startTimer():
	global timerStart
	timerStart = time.time()
	sendAll(users, 'timer:%s' % (timerLength))

def roundTimeIsUp():
	# Check if the time has elapsed and update data structures
	global timerStart
	if timerStart != None:
		if time.time() > timerStart + timerLength:
			timerStart = None
			return True
	return False

def isTeamChosen():
	global state
	playersNeeded = gameState.playersOnTeam()
	currentPlayers = 0
	teamMembers = [x for x in users if x.teamMember == True]
	currentPlayers += len(teamMembers)

	if currentPlayers == playersNeeded:
		# Advance to next game state
		for user in users:
			send(user, 'success:%s' % ('Team Chosen - team voting has begun'))
			for u in teamMembers:
				send(user, 'team_member:%s' % (u.place))
		print('Correct number of players chosen, moving to vote_quest phase')
		state = 'vote_quest'
		startTimer()

def didTeamPass():
	global state
	votes = 0
	players = [x for x in users if x.role != 'spectator']
	for user in players:
		if user.voteAffirmative != None:
			votes += 1

	if votes == len(players):
		print('Everyone has voted for the current team members')
		# Tell everyone who voted what
		fails = 0
		for user in users:
			for u in users:
				send(user, 'success:%s voted %s.' % (u.name, u.voteAffirmative))
			if not user.voteAffirmative:
				fails += 1

		if fails / len(players) >= .5:
			print('Majority voted negatively for the current team')
			#increment attemptedTeams
			gameState.attemptedTeams += 1
			# If there have been 5 failures to go on the quest,
			# then the quest fails
			if gameState.attemptedTeams > 5:
				#hide party counter 5, show party counter 1
				gameState.attemptedTeams = 1
				missionFail(gameState.questNumber)
				gameState.questOutcomes[gameState.questNumber-1] = 'evil'
				gameState.questNumber += 1
			#show correct party counter
			sendAll(users, 'quest_no_go:%s' % (gameState.attemptedTeams))
			for user in users:
				send(user, 'success:Current team failed - choosing new leader.')
			startRound()
		else:
			print('Current team passed, going on quest')
			for user in users:
				send(user, 'success:Current team passed - going on quest.')
			resetVotes()
			startTimer()
			state = 'quest_success_or_fail'

def didQuestPass():
	global state
	votesNeeded = gameState.playersOnTeam()
	votes = 0
	teamMembers = [x for x in users if x.teamMember == True]
	for user in teamMembers:
		if user.voteAffirmative != None:
			votes += 1

	if votes == votesNeeded:
		success = True
		for user in teamMembers:
			if user.voteAffirmative == False:
				success = False

		if success:
			sendAll(users, 'mission_success:%s' % (gameState.questNumber))
			gameState.questOutcomes[gameState.questNumber-1] = 'good'
		else:
			sendAll(users, 'mission_fail:%s' % (gameState.questNumber))
			gameState.questOutcomes[gameState.questNumber-1] = 'evil'
		gameState.questNumber += 1

		if gameState.questOutcomes.count('good') == 3:
			print('Good has won 3 rounds - go to assassinate phase')
			state = 'assassinate'
			for user in users:
				send(user, 'state:assassinate')
		elif gameState.questOutcomes.count('evil') == 3:
			print('Evil has won 3 rounds - game over')
			state = 'game_over'
			for user in users:
				send(user, 'win:evil')
		else:
			startRound()

def doGameLogic():
	global state

	if state == 'choose_team':
		isTeamChosen()
	elif state == 'vote_quest':
		didTeamPass()
	elif state == 'quest_success_or_fail':
		didQuestPass()
	elif state == 'assassinate':
		# Just pass here, when assassin chooses target the game state will advance
		# automatically because there is nothing to wait for
		pass
	elif state == 'not_started':
		# Just pass here, when game admin starts the game the state will advance
		# automatically because there is nothing to wait for after that
		pass

def doDefaultTimeOut():
	global state
	print('Timer elapsed')
	if state == 'choose_team':
		print('choose_team time up, choosing team randomly')
		playersNeeded = gameState.playersOnTeam()
		onTeam = [x for x in players if x.teamMember == True]
		notOnTeam = [x for x in players if x.teamMember == False]
		random.shuffle(notOnTeam)

		while len(onTeam) < playersNeeded:
			x = notOnTeam.pop(0)
			x.teamMember = True
			onTeam.append(x)
	elif state == 'vote_quest':
		print('vote_quest time up, voting affirmatively for everyone who hasn\'t voted')
		voter = [x for x in players if x.voteAffirmative == None]
		for u in voter:
			if u.isGood():
				u.voteAffirmative = True
			else: # Split for now in case we want to randomize the evil players vote
				u.voteAffirmative = True
	elif state == 'quest_success_or_fail':
		print('quest_success_or_fail time up, voting affirmatively for good team members, else negatively')
		onTeam = [x for x in players if x.teamMember == True]
		for u in onTeam:
			if u.isGood():
				u.voteAffirmative = True
			else:
				u.voteAffirmative = False
	elif state == 'assassinate':
		# TODO
		pass

def assassinVote(user, place):
	if user.role == 'nissassa' and state == 'assassinate':
		if players[place-1].role == 'merlin':
			sendAll(users, 'win:evil')
		else:
			sendAll(users, 'win:good')

def addToTeam(user, place):
	playersOnTeam = [x for x in players if x.teamMember == True]
	maxPlayers = gameState.playersOnTeam()

	if user.teamLeader and len(playersOnTeam) < maxPlayers:
		for p in players:
			if p.place == int(place):
				p.teamMember = True
				send(p, 'team:member')

def playGame():
	try:
		userId = 1
		while True:
			if roundTimeIsUp():
				doDefaultTimeOut()

			doGameLogic()

			client = ws.accept()
			if client is not None:
				# figure out who they are and add to list
				user = User(client, userId)
				userId = userId + 1
				users.append(user)

			# For each client, see if they sent anything
			for user in users:
				if user.disconnected:
					continue
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
					sendAll(users, 'chat:%s:%s' % (htmlEncode(user.name), htmlEncode(action[1])))
				elif action[0] == 'name':
					# When someone updates their name, tell everyone
					# Could potentially be abused? TODO: rate limit? only allow once?
					# Check for duplicate name?
					regex = r'(\w+).*'
					match = re.match(regex, action[1])
					if match:
						user.name = match.group(1)
						sendAll(users, '%s:%s' % (user.id, htmlEncode(user.name)))
					pass
				elif action[0] == 'game':
					gameAction(user, action[1])
				elif action[0] == 'assassinate':
					assassinVote(user, action[1])
				elif action[0] == 'quester':
					addToTeam(user, action[1])
				elif action[0] == 'session':
					reconnectUser(user, action[1])
				elif action[0] == 'vote':
					# Should be either reject/approve or success/fail depending on what vote is for
					if user.role != 'spectator':
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

if __name__ == '__main__':
	playGame()