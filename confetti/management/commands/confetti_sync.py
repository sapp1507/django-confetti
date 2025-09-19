from django.core.management.base import BaseCommand
from confetti.seed import seed_from_settings


class Command(BaseCommand):
    help = (
        "Sync Confetti categories/definitions from settings.CONFETTI. "
        "By default only creates missing items. "
        "Use --update to update safe fields (title/description/enabled/editable). "
        "Use --update-defaults to also update default/choices/type."
    )

    def add_arguments(self, parser):
        parser.add_argument('--update', action='store_true', help='Update safe fields (title/description/enabled/editable)')
        parser.add_argument('-update-defaults', action='store_true', help='Update default/choices/type')
        parser.add_argument('--categories-only', action='store_true', help='Only sync categories')
        parser.add_argument('--definitions-only', action='store_true', help='Only sync definitions')
        parser.add_argument('--dry-run', action='store_true', help='Dry run')

    def handle(self, *args, **options):
        update = options['update']
        update_defaults = options['update_defaults']
        only = None
        if options['categories_only']:
            only = 'categories'
        elif options['definitions_only']:
            only = 'definitions'

        if options['dry_run']:
            from django.db import transaction
            try:
                with transaction.atomic():
                    stats = seed_from_settings(
                        update=update,
                        update_defaults=update_defaults,
                        only=only,
                        stdout=self.stdout,
                        stderr=self.stderr
                    )
                    self.stdout.write(self.style.WARNING(f'[dry-run] planned stats: {stats}'))
                    raise  RuntimeError('dry-run rollback')
            except RuntimeError:
                self.stdout.write(self.style.SUCCESS('[dry-run] completed successfully'))
                return

        stats = seed_from_settings(
            update=update,
            update_defaults=update_defaults,
            only=only,
            stdout=self.stdout,
            stderr=self.stderr
        )
        self.stdout.write(self.style.SUCCESS(f'completed successfully: {stats}'))
