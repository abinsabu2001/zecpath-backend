import os
from datetime import datetime, timezone

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a timestamped database backup"

    def handle(self, *args, **options):
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        backup_file = os.path.join(
            backup_dir,
            f"backup_{timestamp}.json"
        )

        with open(backup_file, "w", encoding="utf-8") as file:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                stdout=file,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backup created successfully: {backup_file}"
            )
        )