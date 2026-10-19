"""
Unit test suite for HelpDesk AI Authentication & User Security.
Validates:
1. PBKDF2-HMAC-SHA256 password hashing and timing-safe verification.
2. Unique salt generation and resistance to rainbow tables.
3. Password strength evaluator and requirement checks.
4. Email syntax validation.
5. Insecure demo accounts are NOT auto-seeded into the database.
6. Self-assignment of privileged roles is strictly prohibited.
7. Authorized privileged role provisioning succeeds when allow_privileged=True.
8. Registration workflow, duplicate email rejection, and input validation.
9. Authentication workflow, invalid credentials rejection, and session metadata.
10. Dynamic auth secret generation without hardcoded fallbacks.
11. Safe profile retrieval (no hashes or salts leaked).
12. Password change workflow.
"""

import unittest
import os
import sqlite3
import tempfile
import auth


class TestHelpdeskAuth(unittest.TestCase):
    """Test suite covering genuine local authentication controls."""

    def setUp(self):
        auth.init_auth_db()

    def test_password_hashing_and_verification(self):
        pwd = "SecurePassword123!"
        pwd_hash, salt_hex = auth.hash_password(pwd)
        
        self.assertIsInstance(pwd_hash, str)
        self.assertIsInstance(salt_hex, str)
        self.assertEqual(len(pwd_hash), 64)  # 256-bit SHA256 in hex
        self.assertEqual(len(salt_hex), 32)  # 16 bytes in hex

        # Correct password must verify
        self.assertTrue(auth.verify_password(pwd, salt_hex, pwd_hash))

        # Incorrect password must fail
        self.assertFalse(auth.verify_password("WrongPassword123!", salt_hex, pwd_hash))
        self.assertFalse(auth.verify_password("", salt_hex, pwd_hash))

    def test_unique_salts_produce_distinct_hashes(self):
        pwd = "IdenticalPassword99#"
        hash1, salt1 = auth.hash_password(pwd)
        hash2, salt2 = auth.hash_password(pwd)

        self.assertNotEqual(salt1, salt2)
        self.assertNotEqual(hash1, hash2)

    def test_email_validation(self):
        valid_emails = [
            "alex.turner@enterprise.internal",
            "jane.doe@company.org",
            "support-team@it-domain.co.uk",
            "user123@sub.domain.net"
        ]
        for email in valid_emails:
            self.assertTrue(auth.validate_email(email), f"Expected {email} to be valid")

        invalid_emails = [
            "",
            "plainaddress",
            "@missingusername.com",
            "username@.com",
            "username@domain..com",
            "spaces in@domain.com"
        ]
        for email in invalid_emails:
            self.assertFalse(auth.validate_email(email), f"Expected {email} to be invalid")

    def test_password_strength_calculation(self):
        # Empty
        s0 = auth.calculate_password_strength("")
        self.assertEqual(s0["score"], 0)

        # Weak (only lowercase, short)
        s1 = auth.calculate_password_strength("abc")
        self.assertIn(s1["score"], [0, 1])
        self.assertFalse(s1["checks"]["min_length"])

        # Fair (mixed case, numbers, but short)
        s2 = auth.calculate_password_strength("Pass1")
        self.assertFalse(s2["checks"]["min_length"])

        # Good (8+ chars, upper, lower, numbers)
        s3 = auth.calculate_password_strength("Password123")
        self.assertGreaterEqual(s3["score"], 3)
        self.assertTrue(s3["checks"]["min_length"])
        self.assertTrue(s3["checks"]["has_upper"])
        self.assertTrue(s3["checks"]["has_lower"])
        self.assertTrue(s3["checks"]["has_digit"])

        # Very Strong (8+ chars, upper, lower, numbers, symbols)
        s4 = auth.calculate_password_strength("P@ssw0rd_2026!#")
        self.assertEqual(s4["score"], 4)
        self.assertEqual(s4["percent"], 100)
        self.assertTrue(all(s4["checks"].values()))

    def test_insecure_demo_user_not_auto_seeded(self):
        """Verifies that init_auth_db() does not automatically seed insecure demo accounts."""
        temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_db_fd)
        orig_db_path = auth.DB_PATH
        try:
            auth.DB_PATH = temp_db_path
            auth.init_auth_db()
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            conn.close()
            self.assertEqual(count, 0, "init_auth_db() must not automatically seed demo accounts into a new database")
        finally:
            auth.DB_PATH = orig_db_path
            if os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except Exception:
                    pass

    def test_prevent_privileged_role_self_assignment(self):
        """Self-registering users must NOT be able to assign themselves privileged roles."""
        test_email = "attacker@enterprise.internal"
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        # Attempt to self-register as SecOps Incident Analyst
        ok, msg, user = auth.register_user(
            test_email,
            "Attacker",
            "StrongPass123!",
            "StrongPass123!",
            role="SecOps Incident Analyst",
            allow_privileged=False
        )
        self.assertFalse(ok)
        self.assertIsNone(user)
        self.assertIn("Self-assignment of privileged roles is not permitted", msg)

        # Attempt to self-register as IT Service Desk Specialist
        ok, msg, user = auth.register_user(
            test_email,
            "Attacker",
            "StrongPass123!",
            "StrongPass123!",
            role="IT Service Desk Specialist",
            allow_privileged=False
        )
        self.assertFalse(ok)
        self.assertIsNone(user)
        self.assertIn("Self-assignment of privileged roles is not permitted", msg)

    def test_authorized_privileged_role_registration(self):
        """Authorized registration with allow_privileged=True successfully assigns privileged role."""
        test_email = "admin.provisioned@enterprise.internal"
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        try:
            ok, msg, user = auth.register_user(
                test_email,
                "Admin Staff",
                "StrongPass123!",
                "StrongPass123!",
                role="SecOps Incident Analyst",
                allow_privileged=True
            )
            self.assertTrue(ok)
            self.assertIsNotNone(user)
            self.assertEqual(user["role"], "SecOps Incident Analyst")
        finally:
            conn = auth.get_db_connection()
            conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
            conn.commit()
            conn.close()

    def test_auth_secret_no_hardcoded_fallback(self):
        """Verifies get_auth_secret() does not return hardcoded fallback secrets."""
        secret = auth.get_auth_secret()
        self.assertIsInstance(secret, str)
        self.assertGreaterEqual(len(secret), 32)
        self.assertNotEqual(secret, "helpdesk-prod-hmac-salt-secret-key-2026", "Hard-coded fallback secret must not be used")

    def test_user_registration_and_login_flow(self):
        test_email = "test.employee@enterprise.internal"
        # Clean up if existed from prior run
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        # 1. Registration with mismatched password fails
        ok, msg, _ = auth.register_user(test_email, "Test Employee", "StrongPass123!", "MismatchPass123!")
        self.assertFalse(ok)
        self.assertIn("do not match", msg)

        # 2. Registration with short password fails
        ok, msg, _ = auth.register_user(test_email, "Test Employee", "Short1!", "Short1!")
        self.assertFalse(ok)
        self.assertIn("at least 8 characters", msg)

        # 3. Standard employee registration succeeds
        ok, msg, user = auth.register_user(
            test_email,
            "Test Employee",
            "StrongPass123!",
            "StrongPass123!",
            role="Employee / Incident Reporter"
        )
        self.assertTrue(ok)
        self.assertEqual(user["email"], test_email)
        self.assertEqual(user["role"], "Employee / Incident Reporter")

        # 4. Duplicate registration fails
        ok_dup, msg_dup, _ = auth.register_user(
            test_email,
            "Test Duplicate",
            "StrongPass123!",
            "StrongPass123!"
        )
        self.assertFalse(ok_dup)
        self.assertIn("already exists", msg_dup)

        # 5. Login with invalid password fails
        ok_bad, _, _ = auth.authenticate_user(test_email, "WrongPassword!")
        self.assertFalse(ok_bad)

        # 6. Login with valid password succeeds
        ok_good, msg_good, auth_user = auth.authenticate_user(test_email, "StrongPass123!")
        self.assertTrue(ok_good)
        self.assertEqual(auth_user["email"], test_email)
        self.assertEqual(auth_user["full_name"], "Test Employee")
        self.assertEqual(auth_user["role"], "Employee / Incident Reporter")

        # Clean up
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

    def test_no_sensitive_secrets_in_profile(self):
        test_email = "profile.check@enterprise.internal"
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        try:
            auth.register_user(
                test_email,
                "Profile Check",
                "StrongPassword123!",
                "StrongPassword123!"
            )
            profile = auth.get_user_by_email(test_email)
            self.assertIsNotNone(profile)
            self.assertNotIn("password_hash", profile)
            self.assertNotIn("salt", profile)
            self.assertIn("email", profile)
            self.assertIn("full_name", profile)
            self.assertIn("role", profile)
        finally:
            conn = auth.get_db_connection()
            conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
            conn.commit()
            conn.close()

    def test_change_password_flow(self):
        test_email = "pwd.change.test@enterprise.internal"
        conn = auth.get_db_connection()
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        try:
            auth.register_user(
                test_email,
                "Password Changer",
                "InitialPass123!",
                "InitialPass123!"
            )
            
            # 1. Incorrect current password fails
            ok, msg = auth.change_password(test_email, "WrongPass123!", "NewSecretPass2026!", "NewSecretPass2026!")
            self.assertFalse(ok)
            self.assertIn("incorrect", msg.lower())

            # 2. Mismatched confirmation fails
            ok, msg = auth.change_password(test_email, "InitialPass123!", "NewSecretPass2026!", "DifferentPass2026!")
            self.assertFalse(ok)
            self.assertIn("do not match", msg.lower())

            # 3. Weak new password fails
            ok, msg = auth.change_password(test_email, "InitialPass123!", "weak", "weak")
            self.assertFalse(ok)

            # 4. Valid update succeeds
            ok, msg = auth.change_password(test_email, "InitialPass123!", "NewValidPass2026!", "NewValidPass2026!")
            self.assertTrue(ok)
            self.assertIn("successfully", msg.lower())

            # 5. Old password no longer works
            ok_old, _, _ = auth.authenticate_user(test_email, "InitialPass123!")
            self.assertFalse(ok_old)

            # 6. New password works
            ok_new, _, user_data = auth.authenticate_user(test_email, "NewValidPass2026!")
            self.assertTrue(ok_new)
            self.assertIsNotNone(user_data)
        finally:
            conn = auth.get_db_connection()
            conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
            conn.commit()
            conn.close()


if __name__ == "__main__":
    unittest.main()
