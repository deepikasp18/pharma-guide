#!/usr/bin/env python3
"""
Generate security keys for PharmaGuide Health Companion

This script generates the required SECRET_KEY and ENCRYPTION_KEY
for the application.

Usage:
    python scripts/generate_keys.py
    
    # Or make it executable and run directly:
    chmod +x scripts/generate_keys.py
    ./scripts/generate_keys.py
"""
import secrets
from cryptography.fernet import Fernet


def generate_secret_key() -> str:
    """Generate a secure random secret key for JWT tokens"""
    return secrets.token_urlsafe(32)


def generate_encryption_key() -> str:
    """Generate a Fernet encryption key for AES-256 encryption"""
    return Fernet.generate_key().decode()


def main():
    print("=" * 70)
    print("PharmaGuide Security Keys Generator")
    print("=" * 70)
    print()
    
    # Generate keys
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    
    # Display keys
    print("Generated Security Keys:")
    print("-" * 70)
    print()
    print("SECRET_KEY (for JWT tokens):")
    print(secret_key)
    print()
    print("ENCRYPTION_KEY (for PII/PHI encryption):")
    print(encryption_key)
    print()
    print("-" * 70)
    print()
    
    # Instructions
    print("Instructions:")
    print("1. Copy these keys to your .env file")
    print("2. Never commit these keys to version control")
    print("3. Use different keys for each environment (dev, staging, prod)")
    print("4. Store production keys in a secure secrets manager")
    print()
    
    # Generate .env snippet
    print("Add these lines to your .env file:")
    print("-" * 70)
    print(f"SECRET_KEY={secret_key}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print("-" * 70)
    print()
    
    # Offer to write to file
    response = input("Would you like to append these to .env file? (y/N): ").strip().lower()
    
    if response == 'y':
        try:
            with open('.env', 'a') as f:
                f.write('\n# Generated security keys\n')
                f.write(f'SECRET_KEY={secret_key}\n')
                f.write(f'ENCRYPTION_KEY={encryption_key}\n')
            print("✅ Keys appended to .env file successfully!")
        except Exception as e:
            print(f"❌ Error writing to .env file: {e}")
            print("Please copy the keys manually.")
    else:
        print("Keys not written to file. Please copy them manually.")
    
    print()
    print("⚠️  IMPORTANT: Keep these keys secure and never share them!")
    print()


if __name__ == "__main__":
    main()
