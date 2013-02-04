import pam
from functools import wraps

def check_auth(username, password):
	return True  #pam.authenticate(username, password, 'cloud')
                
def authenticate():
	return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})
                                    
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
              return authenticate()
        return f(*args, **kwargs)
    return decorated  
