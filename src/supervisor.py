import http.client
import socket
import xmlrpc.client

SUPERVISOR_SOCK_PATH = '/tmp/supervisor.sock'

class UnixStreamHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over Unix socket."""
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.host)

class UnixStreamTransport(xmlrpc.client.Transport):
    """XML-RPC transport over Unix socket."""
    def __init__(self, socket_path):
        self.socket_path = socket_path
        super().__init__()

    def make_connection(self, host):
        return UnixStreamHTTPConnection(self.socket_path)

def _get_supervisor_client():
    return xmlrpc.client.ServerProxy(
        'http://127.0.0.1',
        transport=UnixStreamTransport(SUPERVISOR_SOCK_PATH)
    )

def start_photon():
    try:
        server = _get_supervisor_client()
        print("Attempting to start 'photon' process...")
        server.supervisor.startProcess('photon')
        print("Successfully sent 'start' command to 'photon' process.")
    except Exception as e:
        print(f"Error starting photon via supervisor: {e}")

def stop_photon():
    try:
        server = _get_supervisor_client()
        print("Attempting to stop 'photon' process...")
        server.supervisor.stopProcess('photon')
        print("Successfully sent 'stop' command to 'photon' process.")
    except Exception as e:
        print(f"Error stopping photon via supervisor: {e}")
