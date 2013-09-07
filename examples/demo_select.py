# demo inspired from http://tour.golang.org/#67

from offset import makechan, select, go, run, maintask

def fibonacci(c, quit):
    x, y = 0, 1
    while True:
        ret = select(c.if_send(x), quit.if_recv())
        if ret == c.if_send(x):
            x, y = y, x+y
        elif ret == quit.if_recv():
            print("quit")
            return

@maintask
def main():
    c = makechan()
    quit = makechan()
    def f():
        for i in range(10):
            print(c.recv())

        quit.send(0)

    go(f)
    fibonacci(c, quit)

if __name__ == "__main__":
    run()
