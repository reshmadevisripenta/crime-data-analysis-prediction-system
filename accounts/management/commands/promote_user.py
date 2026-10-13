import sys
from django.core.management.base import BaseCommand, CommandError
from accounts.models import User


class Command(BaseCommand):
    help = 'Change a user\'s role (admin, analyst, or viewer)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the account to update')
        parser.add_argument(
            '--role', type=str, required=True,
            choices=['admin', 'analyst', 'viewer'],
            help='New role to assign (admin, analyst, or viewer)'
        )
        parser.add_argument(
            '--no-input', action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        username = options['username']
        new_role = options['role']
        no_input = options['no_input']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')

        old_role = user.get_role_display()
        new_role_display = dict(User.ROLE_CHOICES).get(new_role, new_role)

        if user.role == new_role:
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already has role "{old_role}". No changes made.')
            )
            return

        self.stdout.write(f'\nUser:         {username}')
        self.stdout.write(f'Email:        {user.email}')
        self.stdout.write(f'Current role: {old_role}')
        self.stdout.write(f'New role:     {new_role_display}\n')

        if not no_input:
            confirm = input(f'Change role from "{old_role}" to "{new_role_display}"? [y/N] ')
            if confirm.lower() not in ('y', 'yes'):
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        user.role = new_role
        # If promoting to admin, also grant staff access for Django admin panel
        if new_role == 'admin':
            user.is_staff = True
        user.save(update_fields=['role', 'is_staff'] if new_role == 'admin' else ['role'])

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully changed "{username}" role from "{old_role}" to "{new_role_display}".'
            )
        )
