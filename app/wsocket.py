import socket
import hashlib
import base64
import re

def getField(key, s):
	regex = re.compile(key + r': (.*)')
	s = s.decode()
	for line in s.split('\r\n'):
		m = regex.search(line)
		if m:
			return m.groups()[0]
	raise ValueError('No matching key was found for' + key)

def getPath(s):
	'''Get path of get request, e.g. returns "abc" from "GET /abc HTTP/1.1"'''
	regex = re.compile(r'GET /(.*?) HTTP/1.1')
	s = s.decode()
	for line in s.split('\r\n'):
		m = regex.search(line)
		if m:
			return m.groups()[0]
	raise ValueError('Path not found in GET request')

class WSocket:

	WEBSOCKETMAGICSTRING = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
	sock = None
	verbose = True

	def __init__(self, host, port, timeout):
		'''To create an instance of this class, pass a socket that is listening, and the constructor
		will accept a connection and upgrade to a websocket'''
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind((host, port))
		self.sock.listen(10) # arg is for backlogged connections before not accepting new ones

	def accept(self):
		# Get request
		try:
			self.sock.setblocking(0)
			connection_tuple = self.sock.accept()
			if self.verbose:
				print("Accepted connection from %s" % (connection_tuple[1][0]))

			# Recv connection request and send back accept
			recvd = connection_tuple[0].recv(4096)
			if self.verbose:
				print('\033[32m' + recvd.decode('ascii') + '\033[0m')
			if len(recvd) > 0:
				sha1 = hashlib.sha1()
				sha1.update(bytes(getField('Sec-WebSocket-Key', recvd) + self.WEBSOCKETMAGICSTRING, 'ascii'))
				s = b'HTTP/1.1 101 Switching Protocols\r\n'
				s += b'Upgrade: websocket\r\n'
				s += b'Connection: Upgrade\r\n'
				s += b'Sec-WebSocket-Accept: ' + base64.b64encode(sha1.digest()) + b'\r\n'
				s += b'Sec-WebSocket-Protocol: ' + bytes(getField('Sec-WebSocket-Protocol', recvd), 'ascii') + b'\r\n'
				s += b'\r\n'
				if self.verbose:
					print('\033[34m' + s.decode('utf-8') + '\033[0m')
				connection_tuple[0].send(s)

			return connection_tuple[0]
		except BlockingIOError:
			# Since this is non-blocking, sock.accept() throws an exception if there's
			# not a client already trying to connect
			return None
		except TimeoutError:
			return None

	@staticmethod
	def send(socket, data):
		'''Encode and send data, who knows why it's so cryptically sent...'''
		try:
			b = []
			b.append(129)

			bytesRaw = data.encode()
			length = len(bytesRaw)
			if length <= 125 :
				b.append(length)
			elif length >= 126 and length <= 65535:
				b.append(126)
				b.append((length >> 8) & 255)
				b.append(length & 255)
			else:
				b.append(127 )
				b.append((length >> 56) & 255)
				b.append((length >> 48) & 255)
				b.append((length >> 40) & 255)
				b.append((length >> 32) & 255)
				b.append((length >> 24) & 255)
				b.append((length >> 16) & 255)
				b.append((length >>  8) & 255)
				b.append(length & 255)

			b = bytes(b)
			b = b + bytesRaw
			print('\033[34m' + data + '\033[0m')
			socket.send(b)
			return True
		except BlockingIOError:
			return False
		except TimeoutError:
			return False

	@staticmethod
	def recv(socket, size):
		'''Recieve and decode data'''
		try:
			socket.settimeout(0)
			recvd = socket.recv(size)
			byteArray = recvd
			if len(byteArray) > 0:
				datalength = byteArray[1] & 127
				indexFirstMask = 2 
				if datalength == 126:
					indexFirstMask = 4
				elif datalength == 127:
					indexFirstMask = 10
				masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
				indexFirstDataByte = indexFirstMask + 4
				decodedChars = []
				i = indexFirstDataByte
				j = 0
				while i < len(byteArray):
					decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
					i += 1
					j += 1

				ret = u''.join(decodedChars).encode('utf-8')
				print('\033[32m' + ret.decode('utf-8') + '\033[0m')
				return ret
			else:
				return None
		except BlockingIOError:
			return None
		except TimeoutError:
			return None

	def close(self):
		'''Close socket'''
		self.sock.close()
