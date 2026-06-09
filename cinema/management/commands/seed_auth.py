from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from cinema.management.commands._seed_data import AUTH_USERS


class Command(BaseCommand):
    help = "Seed demo authentication groups and users."

    @transaction.atomic
    def handle(self, *args, **options):
        groups = {}
        created_groups = 0
        created_users = 0

        for _username, _password, role in AUTH_USERS:
            group, created = Group.objects.get_or_create(name=role)
            groups[role] = group
            created_groups += created

        for username, password, role in AUTH_USERS:
            user, created = User.objects.get_or_create(username=username)
            user.email = f"{username}@silverscreen.local"
            user.set_password(password)
            user.save()
            user.groups.add(groups[role])
            created_users += created

        updated_users = len(AUTH_USERS) - created_users
        self.stdout.write(
            self.style.SUCCESS(
                f"Authentication data seeded ({created_groups} groups created, "
                f"{created_users} users created, {updated_users} users updated)."
            )
        )
