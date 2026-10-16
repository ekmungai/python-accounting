from python_accounting.config import Config, default_configuration


def test_configure_dates():
    """Configuring dates sets the report date formats and leaves hashing unchanged."""
    configuration = Config(config_file=default_configuration)
    hashing = dict(configuration.hashing)

    configuration.configure_dates(short="%d/%m/%Y", long="%B %d, %Y")

    assert configuration.dates == {"short": "%d/%m/%Y", "long": "%B %d, %Y"}
    assert configuration.hashing == hashing
