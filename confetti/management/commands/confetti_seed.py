from django.core.management.base import BaseCommand
from confetti.seed import seed_from_settings
from confetti.conf import confetti_settings

class Command(BaseCommand):
    help = 'Создает отсутствующие настройки из settings.CONFETTI'

    def add_arguments(self, parser):
        parser.add_argument('--categories-only', action='store_true', help='Создать только категории')
        parser.add_argument('--definitions-only', action='store_true', help='Создать настройки')

    def handle(self, *args, **options):
        only = None
        if options.get('categories-only'):
            only = 'categories'
        if options.get('definitions-only'):
            only = 'definitions'

        stats = seed_from_settings(
            update=False,
            only=only,
            stdout=self.stdout,
            stderr=self.stderr,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Создано {stats["created_definitions"]} настроек и {stats["created_categories"]} категорий'
            )
        )
