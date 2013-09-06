from offset import makechan, maintask, run


@maintask
def main():
    c = makechan(2)
    c.send(1)
    c.send(2)
    print(c.recv())
    print(c.recv())


if __name__ == "__main__":
    run()
