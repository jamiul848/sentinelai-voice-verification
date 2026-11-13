"""Sentinel Voice - Administrative User Seed / Elevation Utility.

Usage:
    python scripts/create_admin.py --email admin@sentinelvoice.io --password AdminPassword!123
    python scripts/create_admin.py --promote abc@gmail.com
"""

import argparse
import asyncio
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath("."))

from sentinelai.auth.password import hash_password
from sentinelai.database.connection import get_session_factory
from sentinelai.database.repositories.user_repository import UserRepository


async def create_or_promote_admin(email: str, password: str = None, full_name: str = None, promote_only: bool = False):
    factory = get_session_factory()
    async with factory() as session:
        repo = UserRepository(session)

        # Ensure ADMIN and USER roles exist
        admin_role = await repo.get_role_by_name("ADMIN")
        if not admin_role:
            admin_role = await repo.create_role(name="ADMIN", description="Administrator")

        user_role = await repo.get_role_by_name("USER")
        if not user_role:
            user_role = await repo.create_role(name="USER", description="Standard User")

        user = await repo.get_by_email(email)
        if user:
            role_ids = {r.id for r in user.roles}
            if admin_role.id not in role_ids:
                await repo.assign_role(user.id, admin_role.id)
            if password:
                user.hashed_password = hash_password(password)
            user.is_active = True
            await session.commit()
            print(f"Successfully elevated existing user '{email}' to ADMIN role!")
            return user
        elif promote_only:
            print(f"Error: User '{email}' does not exist.")
            sys.exit(1)
        else:
            if not password:
                password = "AdminPassword!123"
            pw_hash = hash_password(password)
            user = await repo.create_user(
                email=email,
                hashed_password=pw_hash,
                full_name=full_name or "System Administrator",
                is_active=True,
                is_verified=True,
            )
            await repo.assign_role(user.id, user_role.id)
            await repo.assign_role(user.id, admin_role.id)
            await session.commit()
            print(f"Successfully created new ADMIN user: '{email}'")
            print(f"Password: {password}")
            return user


def main():
    parser = argparse.ArgumentParser(description="Create or elevate a Sentinel Voice administrator account.")
    parser.add_argument("--email", default="admin@sentinelvoice.io", help="Admin email address")
    parser.add_argument("--password", default="AdminPassword!123", help="Password for admin account")
    parser.add_argument("--name", default="System Administrator", help="Full name of admin")
    parser.add_argument("--promote", action="store_true", help="Only elevate existing account without creating new")

    args = parser.parse_args()
    asyncio.run(create_or_promote_admin(email=args.email, password=args.password, full_name=args.name, promote_only=args.promote))


if __name__ == "__main__":
    main()

