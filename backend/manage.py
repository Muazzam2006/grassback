                     
import os
import sys
                                                                     
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
