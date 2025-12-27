#!/usr/bin/env python3
"""
Admin User Creation Script
Creates an administrator user for the Jon Circle App.
"""

import sys
import getpass
from database_improved import create_user, get_user_by_username, init_db, migrate_db
from security_config import SecurityConfig, validate_email, validate_username


def create_admin_user():
    """Interactive script to create an admin user."""
    print("\n" + "="*60)
    print("JON CIRCLE APP - Admin User Creation")
    print("="*60 + "\n")

    # Initialize database
    print("Initializing database...")
    init_db()
    migrate_db()
    print("✓ Database ready\n")

    # Get username
    while True:
        username = input("Enter admin username: ").strip()

        if not username:
            print("❌ Username cannot be empty")
            continue

        is_valid, error_msg = validate_username(username)
        if not is_valid:
            print(f"❌ {error_msg}")
            continue

        # Check if user exists
        existing_user = get_user_by_username(username)
        if existing_user:
            print(f"❌ Username '{username}' already exists")
            continue

        break

    # Get email
    while True:
        email = input("Enter admin email: ").strip()

        if not email:
            print("❌ Email cannot be empty")
            continue

        if not validate_email(email):
            print("❌ Invalid email format")
            continue

        break

    # Get password
    while True:
        password = getpass.getpass("Enter admin password: ")

        if not password:
            print("❌ Password cannot be empty")
            continue

        is_valid, error_msg = SecurityConfig.validate_password(password)
        if not is_valid:
            print(f"❌ {error_msg}")
            print("\nPassword requirements:")
            print(f"  - At least {SecurityConfig.PASSWORD_MIN_LENGTH} characters")
            if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE:
                print("  - At least one uppercase letter")
            if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE:
                print("  - At least one lowercase letter")
            if SecurityConfig.PASSWORD_REQUIRE_DIGITS:
                print("  - At least one digit")
            if SecurityConfig.PASSWORD_REQUIRE_SPECIAL:
                print("  - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
            print()
            continue

        # Confirm password
        password_confirm = getpass.getpass("Confirm admin password: ")

        if password != password_confirm:
            print("❌ Passwords do not match\n")
            continue

        break

    # Get full name (optional)
    full_name = input("Enter full name (optional): ").strip() or None

    # Confirm creation
    print("\n" + "-"*60)
    print("Admin User Details:")
    print(f"  Username:  {username}")
    print(f"  Email:     {email}")
    print(f"  Full Name: {full_name or 'N/A'}")
    print(f"  Role:      admin")
    print("-"*60)

    confirm = input("\nCreate this admin user? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("\n❌ Admin user creation cancelled")
        sys.exit(0)

    # Create user
    try:
        print("\nCreating admin user...")
        user_id = create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role='admin'
        )

        if user_id:
            print(f"\n✓ Admin user created successfully!")
            print(f"  User ID: {user_id}")
            print(f"  Username: {username}")
            print(f"  Email: {email}")
            print(f"  Role: admin")
            print("\nYou can now log in with these credentials.")
            print("="*60 + "\n")
            return True
        else:
            print("\n❌ Failed to create admin user")
            return False

    except Exception as e:
        print(f"\n❌ Error creating admin user: {str(e)}")
        return False


def main():
    """Main entry point."""
    try:
        success = create_admin_user()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Admin user creation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
