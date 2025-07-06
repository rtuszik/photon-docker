import xmlrpc.client
import socket

SUPERVISOR_SOCK_PATH = '/tmp/supervisor.sock'

def _get_supervisor_client():
    return xmlrpc.client.ServerProxy(
        'http://127.0.0.1',
        transport=xmlrpc.client.Transport(
            make_connection=lambda _, timeout=socket._GLOBAL_DEFAULT_TIMEOUT:
                socket.create_connection((SUPERVISOR_SOCK_PATH,), timeout)
        )
    )

def start_photon():
    try:
        server = _get_supervisor_client()
        server.supervisor.startProcess('photon')
        print("Successfully sent 'start' command to photon process.")
    except Exception as e:
        print(f"Error starting photon via supervisor: {e}")

def stop_photon():
    try:
        server = _get_supervisor_client()
        server.supervisor.stopProcess('photon')
        print("Successfully sent 'stop' command to photon process.")
    except Exception as e:
        print(f"Error stopping photon via supervisor: {e}")
