from offset import go, maintask, run
from offset.net import sock


import signal
from offset.core import kernel

def handle(*args):
    print("quit")

@maintask
def main():
    kernel.signal_enable(signal.SIGINT, handle)

    fd = sock.bind_socket("tcp", ('127.0.0.1', 0))
    print(fd.name())
    while True:
        fd1 = fd.accept()
        print("accepted %s" % fd1.name())
        fd1.write(b"ok\n")
        fd1.close()

run()
