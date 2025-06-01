class DictType(dict):
    def __init__(self, init) -> None:
        for k, v in init.items():
            self[k] = v
