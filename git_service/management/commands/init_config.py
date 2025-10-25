"""
Management command to initialize default configurations.
"""

from django.core.management.base import BaseCommand
from git_service.models import Configuration


class Command(BaseCommand):
    help = 'Initialize default GitWiki configurations'

    def handle(self, *args, **options):
        self.stdout.write('Initializing default configurations...')

        Configuration.initialize_defaults()

        self.stdout.write(self.style.SUCCESS('Successfully initialized configurations'))

        # Display all configurations
        self.stdout.write('\nCurrent configurations:')
        for config in Configuration.objects.all():
            self.stdout.write(f'  {config.key}: {config.value}')
