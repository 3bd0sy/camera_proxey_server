#!/usr/bin/env python
"""
Script to generate self-signed SSL certificates for HTTPS.
Run this once to create ssl/certificate.crt and ssl/private.key
"""

import subprocess
import sys
from pathlib import Path


def generate_ssl_certificates(days: int = 365):
    """Generate self-signed SSL certificates."""

    ssl_dir = Path(__file__).parent / "ssl"
    ssl_dir.mkdir(exist_ok=True)

    key_file = ssl_dir / "private.key"
    cert_file = ssl_dir / "certificate.crt"

    if key_file.exists() and cert_file.exists():
        print(f"✅ SSL certificates already exist:")
        print(f"   - {key_file}")
        print(f"   - {cert_file}")
        response = input("Regenerate? (y/n): ").strip().lower()
        if response != "y":
            return True

    try:
        print("🔑 Generating private key...")
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_file), "2048"],
            check=True,
            capture_output=True,
        )
        print(f"   ✓ Created: {key_file}")

        print("📜 Generating self-signed certificate...")
        subject = (
            "/C=SA"
            "/ST=Riyadh"
            "/L=Riyadh"
            "/O=MyCompany"
            "/OU=IT"
            "/CN=localhost"
            "/emailAddress=ax.abdo.syrain@gmail.com"
        )

        subprocess.run(
            [
                "openssl",
                "req",
                "-new",
                "-x509",
                "-key",
                str(key_file),
                "-out",
                str(cert_file),
                "-days",
                str(days),
                "-subj",
                subject,
            ],
            check=True,
            capture_output=True,
        )
        print(f"   ✓ Created: {cert_file}")

        print("\n📋 Certificate Information:")
        print("-" * 60)
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_file), "-text", "-noout"],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.split("\n"):
            if any(
                x in line
                for x in [
                    "Subject:",
                    "Issuer:",
                    "Not Before",
                    "Not After",
                    "Public-Key",
                ]
            ):
                print(line.strip())

        print("-" * 60)
        print(f"\n✅ SSL certificates generated successfully!")
        print(f"📁 Location: {ssl_dir}/")
        print(f"\n🚀 To enable HTTPS, update config.yaml:")
        print(f"""
server:
  ssl:
    enabled: true
    cert_file: "ssl/certificate.crt"
    key_file: "ssl/private.key"
        """)
        print(f"\n⚠️  Note: This is a self-signed certificate for development only!")
        print(
            f"   For production, use certificates from a trusted Certificate Authority (Let's Encrypt, DigiCert, etc.)"
        )

        return True

    except FileNotFoundError as e:
        print(f"❌ OpenSSL not found! \n {e}")
        print("\n📥 Installation instructions:")
        print(
            "   Windows: Install from https://slproweb.com/products/Win32OpenSSL.html"
        )
        print("   macOS:   brew install openssl")
        print("   Linux:   sudo apt-get install openssl")
        return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def verify_certificates():
    """Verify that SSL certificates are valid."""
    ssl_dir = Path(__file__).parent / "ssl"
    key_file = ssl_dir / "private.key"
    cert_file = ssl_dir / "certificate.crt"

    if not key_file.exists() or not cert_file.exists():
        print(f"❌ SSL certificates not found in {ssl_dir}/")
        print("   Run: python generate_ssl.py")
        return False

    print("✅ SSL certificates found!")
    print(f"   - {key_file}")
    print(f"   - {cert_file}")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate or verify SSL certificates for HTTPS"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Certificate validity in days (default: 365)",
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify existing certificates only"
    )

    args = parser.parse_args()

    if args.verify:
        sys.exit(0 if verify_certificates() else 1)
    else:
        sys.exit(0 if generate_ssl_certificates(args.days) else 1)
