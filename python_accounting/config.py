import toml


class Config:
    """Python Accounting configuration class"""

    testing = {}
    accounts = {}
    transactions = {}
    database = {}
    hashing = {}

    def __init__(self, config_file="config.toml") -> None:
        with open(config_file, "r") as f:
            config = toml.load(f)
            for k, v in config.items():
                setattr(self, k, v)


config = Config()
