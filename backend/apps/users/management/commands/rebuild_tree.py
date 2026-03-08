"""
Management command: rebuild_tree
--------------------------------
Rebuilds the MPTT nested-set fields (lft, rght, tree_id, level) for the
User model using the adjacency list stored in the `parent_id` column.

When to use
-----------
- After a bulk data import that wrote `parent_id` values directly to the DB
  without going through `User.save()` (which normally keeps MPTT in sync).
- After manually patching `parent_id` values in a psql shell or migration.
- After restoring a DB dump that does not include consistent lft/rght values.
- As a periodic idempotent health-check in a maintenance window.

Usage
-----
    python manage.py rebuild_tree

    # Identical outcome using the built-in django-mptt command (all models):
    python manage.py rebuild_mptt
"""
import time

from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = (
        "Rebuild MPTT nested-set fields (lft, rght, tree_id, level) for the "
        "User model. Safe to run on a live database — uses a single transaction."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the number of users that will be processed without committing.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]

        total = User.objects.count()
        self.stdout.write(
            f"Found {total:,} user(s). "
            + ("DRY RUN — no changes will be written." if dry_run else "Rebuilding tree…")
        )

        if dry_run:
            return

        t0 = time.monotonic()
        # MPTTManager.rebuild() wraps the operation in a transaction and
        # re-computes lft/rght/tree_id/level from the parent_id adjacency list.
        User.objects.rebuild()
        elapsed = time.monotonic() - t0

        self.stdout.write(
            self.style.SUCCESS(
                f"User MPTT tree rebuilt successfully in {elapsed:.2f}s "
                f"({total:,} node(s) processed)."
            )
        )
