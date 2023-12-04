import toml


class Config:
    """Python Accounting configuration class"""

    testing = {}
    accounts = {}
    database = {}

    def __init__(self, config_file="config.toml") -> None:
        with open(config_file, "r") as f:
            config = toml.load(f)
            self.testing = config["testing"]
            self.accounts = config["accounts"]
            self.database = config["database"]


config = Config()