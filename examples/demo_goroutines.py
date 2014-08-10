# inspired from http://tour.golang.org/#65


from offset import go, maintask, run
from offset import time

def say(s):
    for i in range(5):
        time.sleep(100 * time.MILLISECOND)
        print(s)

@maintask
def main():
    go(say, "world")
    say("hello")

if __name__ == "__main__":
    run()
