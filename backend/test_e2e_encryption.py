"""Simple test for E2E encryption functionality."""
import sys
from app.services.chat_encryption import chat_encryption_service


def test_encryption():
    """Test encryption and decryption."""
    print("Testing E2E Encryption...")

    # Test data
    user_id_1 = "user-123"
    user_id_2 = "user-456"
    message_content = "Hello, this is a secret message!"

    # Test 1: Encrypt and decrypt for same user
    print("\nTest 1: Encrypt and decrypt for same user")
    encrypted = chat_encryption_service.encrypt_message(message_content, user_id_1)
    print(f"  Original: {message_content}")
    print(f"  Encrypted (bytes): {encrypted[:50]}...")

    decrypted = chat_encryption_service.decrypt_message(encrypted, user_id_1)
    print(f"  Decrypted: {decrypted}")
    assert decrypted == message_content, "Decryption failed!"
    print("  ✓ PASS")

    # Test 2: Different user can't decrypt
    print("\nTest 2: Different user cannot decrypt")
    try:
        decrypted_wrong = chat_encryption_service.decrypt_message(encrypted, user_id_2)
        print("  ✗ FAIL - Should have thrown exception")
        sys.exit(1)
    except ValueError as e:
        print(f"  Expected error: {e}")
        print("  ✓ PASS")

    # Test 3: Same user gets same encryption for same message
    print("\nTest 3: Deterministic key derivation")
    encrypted_again = chat_encryption_service.encrypt_message(message_content, user_id_1)
    # Note: Fernet includes timestamps, so ciphertexts will differ
    # But decryption should work
    decrypted_again = chat_encryption_service.decrypt_message(encrypted_again, user_id_1)
    assert decrypted_again == message_content, "Decryption failed!"
    print("  ✓ PASS")

    # Test 4: Long message
    print("\nTest 4: Long message encryption")
    long_message = "This is a very long message. " * 100
    encrypted_long = chat_encryption_service.encrypt_message(long_message, user_id_1)
    decrypted_long = chat_encryption_service.decrypt_message(encrypted_long, user_id_1)
    assert decrypted_long == long_message, "Long message decryption failed!"
    print(f"  Encrypted {len(long_message)} chars successfully")
    print("  ✓ PASS")

    # Test 5: Unicode/special characters
    print("\nTest 5: Unicode and special characters")
    unicode_message = "Hello 👋 世界 🌍 مرحبا بك 🙏 Здравствуй мир"
    encrypted_unicode = chat_encryption_service.encrypt_message(unicode_message, user_id_1)
    decrypted_unicode = chat_encryption_service.decrypt_message(encrypted_unicode, user_id_1)
    assert decrypted_unicode == unicode_message, "Unicode decryption failed!"
    print(f"  Message: {decrypted_unicode}")
    print("  ✓ PASS")

    print("\n" + "="*50)
    print("All encryption tests passed! ✓")
    print("="*50)


if __name__ == "__main__":
    test_encryption()
