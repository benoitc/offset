# example inspired from http://tour.golang.org/#64

from offset import makechan, go, maintask, run

from offset.core.kernel import kernel
from offset.core import proc

def sum(a, c):
    s = 0
    for v in a:
        s += v
    c.send(s)

@maintask
def main():
    a = [7, 2, 8, -9, 4, 0]

    c = makechan()
    go(sum, a[:len(a)/2], c)
    go(sum, a[len(a)/2:], c)
    x, y = c.recv(), c.recv()

    print(x, y, x+y)

if __name__ == "__main__":
    run()
