#!/usr/bin/python3

from wsocket import *
import time

# empty string here for all available interfaces, same as socket
ws = WSocket('', 1400, 0)
clients = []

# Should ideally fork at some point to allow for an arbitrary number of games
# perhaps once there are enough players is the best time
while True:
	# Allow at most 6 clients
	if len(clients) < 6:
		try:
			client = ws.accept()
			clients.append(client)
		except:
			pass # no clients tried connecting

	# For each client, see if they sent anything
	for c in clients:
		try:
			recvd = ws.recv(c, 4096, 0)
			print("Received %s" % recvd)
			# If they did send something, send it to every client
			# THIS IS THE POINT WHERE WE WILL BE INSPECTING USER INPUT
			# TO SEE IF IT'S A CHAT MESSAGE, AN ATTEMPT AT MAKING A GAME
			# MOVE/VOTE/WHATEVER. IN THE CASE OF A MESSAGE, IT DATA WILL
			# BE SENT TO EVERYONE
			for c2 in clients:
				print("Sending %s" % recvd)
				ws.send(c2, str(recvd))
		except:
			pass # silently continue, client hasn't sent anything
