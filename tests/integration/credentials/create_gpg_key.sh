#!/usr/bin/sh
gpg --batch --passphrase '' --quick-gen-key 'Example User <user@example.com>' ed25519 cert 0
FINGERPRINT=$(gpg --no-auto-check-trustdb --list-secret-keys --with-colons | awk -F: '/^fpr/{print $10; exit}')
gpg --batch --passphrase '' --quick-add-key "$FINGERPRINT" cv25519 encr 0
