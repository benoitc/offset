from offset import *

def test(c, quit):
    x = 0
    while True:
        ret = select(c.if_send(x), quit.if_recv())
        if ret == c.if_send(x):
            x = x + 1
        elif ret == quit.if_recv():
            print("quit")
            return

@maintask
def main():
    c = makechan(5, label="c")
    quit = makechan(label="quit")
    def f():
        for i in range(5):
            print(c.recv())
        quit.send(0)

    go(f)
    test(c, quit)
run()
