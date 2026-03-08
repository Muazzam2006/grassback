#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# ---------------------------------------------------------------------------
# libpq encoding fix — MUST be set before any import that touches psycopg2.
#
# PostgreSQL installed on Windows with a Russian locale sends error messages
# (including authentication failures) in CP1251.  psycopg2 tries to decode
# these with UTF-8 and raises:
#   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2 ...
#
# PGCLIENTENCODING tells libpq to request UTF-8 from the server.
# LC_ALL / LANG override the OS locale so libpq formats messages in English.
# These must be set before _connect() is called inside psycopg2._psycopg.
# ---------------------------------------------------------------------------
os.environ.setdefault("PGCLIENTENCODING", "UTF8")
os.environ.setdefault("LC_ALL", "English_United States.1252")
os.environ.setdefault("LANG", "en_US.UTF-8")
os.environ.setdefault("PGOPTIONS", "-c lc_messages=en_US.UTF-8")


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH? Did you forget to activate "
            "a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
