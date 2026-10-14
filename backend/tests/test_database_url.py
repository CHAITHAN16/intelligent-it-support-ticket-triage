from alembic.config import Config
from sqlalchemy.engine import make_url


def test_database_url_percent_encoded_password_survives_alembic_config():
    # ConfigParser treats '%' as interpolation syntax; Alembic env.py must
    # escape it when setting the option, then SQLAlchemy must parse it once.
    original_password = "prefix%2Fmiddle%40suffix"
    database_url = (
        "postgresql+psycopg://it_support:"
        "prefix%252Fmiddle%2540suffix@postgres:5432/it_support"
    )

    escaped_for_config = make_url(database_url).render_as_string(
        hide_password=False
    ).replace("%", "%%")
    config = Config()
    config.set_main_option("sqlalchemy.url", escaped_for_config)
    parsed = make_url(config.get_main_option("sqlalchemy.url"))

    assert parsed.password == original_password
    assert parsed.host == "postgres"
    assert parsed.database == "it_support"
