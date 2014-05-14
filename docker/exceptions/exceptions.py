class TLSParameterError(ValueError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg + "\n\nTLS configurations should map the Docker CLI client configurations. See http://docs.docker.io/examples/https/ for API details."
