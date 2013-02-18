import pam
from functools import wraps
import time
import logging
import socket
import sys

server_address = '/tmp/auth.sock'
def check_auth(username, password):
        # Create a unix domain socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        message = '\x00'.join([username, password, str(time.time())])
        try:
                sock.connect(server_address)
                sock.sendall(message)
                response = sock.recv(1)
        except socket.error as msg:
                logging.error('Failed to contact authentication service')
                return False
        else:
                return response == '\x01'
	pass

def pam_auth(username, password):
	logging.error('Calling PAM')
        return pam.authenticate(username, password)

if __name__ == '__main__':
        import sys
        import os

	print 'Hehe'
        # Make sure the socket does not already exist
        try:
                os.unlink(server_address)
        except OSError:
                if os.path.exists(server_address):
                        logging.error('Socket path could not be bound')
                        pass

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(server_address)
        # Listen for incoming connections
        sock.listen(1)
        while True:
                connection, client_address = sock.accept()
                try:
			print 'Got connection'
                        data = connection.recv(1024)
                        if data:
                                username, password, timestamp = data.split('\x00', 2)
                                print username, password, timestamp
				if pam_auth(username, password):
                                        connection.sendall('\x01')
                                        pass
                                else:
                                        connection.sendall('\x00')
                                        pass
				pass
			else:
				logging.error('No data sent')
                                
		finally:
			# Clean up the connection
			connection.close()
			pass
		pass
	pass



