import toml


class Config:
    """Python Accounting configuration class"""

    testing: dict
    accounts: dict
    transactions: dict
    database: dict
    hashing: dict
    reports: dict
    dates: dict

    def __init__(self, config_file="config.toml") -> None:
        with open(config_file, "r") as f:
            config = toml.load(f)
            for k, v in config.items():
                setattr(self, k, v)


config = Config()
