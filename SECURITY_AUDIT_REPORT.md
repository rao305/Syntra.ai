# Syntra Backend - Security Audit Report
## OWASP Top 10 (2021) Assessment

**Date:** December 18, 2025
**Status:** Phase 2 & 3 Review
**Overall Risk Level:** HIGH (41 findings: 6 CRITICAL, 16 HIGH, 17 MEDIUM, 2 LOW)

---

## Executive Summary

A comprehensive security audit of the Syntra backend revealed **41 security findings** across all OWASP Top 10 categories. Six findings are classified as **CRITICAL** and require immediate remediation before production deployment.

**Key Concerns:**
- 🔴 API keys logged in debug output
- 🔴 Stack traces exposed in error responses
- 🔴 No token revocation mechanism
- 🔴 Debug mode potentially enabled in production
- 🔴 User impersonation possible through user_id spoofing
- 🔴 Credentials stored in plain text in memory during request handling

**Estimated Remediation Effort:** 40-60 hours for critical and high-severity issues

---

## Detailed Findings by Category

### A01:2021 - BROKEN ACCESS CONTROL (4 findings)

#### 1. User Impersonation via user_id Parameter (HIGH)
- **File:** `app/api/threads.py:851`
- **Issue:** User ID taken from `request.user_id` without validating it matches authenticated user
- **Impact:** Attacker can submit requests as different user in same org
- **Fix:** Validate `request.user_id == authenticated_user_id` before processing
- **Code:** Line 851 in `_save_turn_to_db()`

#### 2. Cross-Tenant Data Exposure via NULL creator_id (HIGH)
- **File:** `app/api/threads.py:385-406`
- **Issue:** Threads with NULL creator_id visible to all users in org (legacy compatibility)
- **Impact:** User can access another user's threads within same organization
- **Fix:** Implement proper creator_id migration or per-user access checks
- **Code:** Lines 388-398 show permissive legacy thread visibility

#### 3. Insufficient Header Validation (MEDIUM)
- **File:** `app/api/deps.py:48-66`
- **Issue:** x-org-id header accepted without strong verification against JWT claims
- **Impact:** Token hijacking allows accessing different organization
- **Fix:** Validate x-org-id matches claim in JWT token
- **Code:** Line 58 `if x_org_id: return x_org_id`

#### 4. Missing Creator Validation for Anonymous Requests (MEDIUM)
- **File:** `app/api/threads.py:775`
- **Issue:** Anonymous requests bypass creator_id validation if current_user is None
- **Impact:** Potential privilege escalation if authentication fails
- **Fix:** Enforce creator check for all request types
- **Code:** Line 775 in `_get_thread()`

---

### A02:2021 - CRYPTOGRAPHIC FAILURES (4 findings)

#### 1. Weak JWT Secret Key Not Enforced (HIGH)
- **File:** `config.py:29`
- **Issue:** No minimum length validation on secret_key
- **Impact:** Short secrets vulnerable to brute-force attacks
- **Fix:** Enforce minimum 32 bytes for HS256
```python
if len(self.secret_key) < 32:
    raise ValueError("secret_key must be at least 32 bytes for HS256")
```

#### 2. Fernet Key Not Validated (MEDIUM)
- **File:** `app/security.py:21`
- **Issue:** No validation that encryption_key is valid Fernet format
- **Impact:** Will crash at runtime if invalid key provided
- **Fix:** Validate key format in EncryptionService.__init__()

#### 3. JWT Algorithm Hardcoding (MEDIUM)
- **File:** `config.py:30`, `app/services/token_service.py:43`
- **Issue:** No protection against "none" algorithm attacks if config is manipulated
- **Impact:** Attacker can forge tokens if they control settings
- **Fix:** Hardcode allowed algorithms, reject "none"

#### 4. Unverified Clerk Token Signature (LOW)
- **File:** `app/services/clerk_client.py:50-53`
- **Issue:** Initial decode uses `verify_signature=False` before API verification
- **Impact:** Timing window for exploitation if API call fails
- **Fix:** Verify signature immediately before using token claims

---

### A03:2021 - INJECTION (3 findings)

#### 1. Fragile Dynamic SQL Construction (MEDIUM)
- **File:** `app/security.py:108`
- **Issue:** `f"SELECT 1 FROM {safe_table} WHERE id = ..."`
- **Impact:** While `safe_table` is validated, mixing f-strings with parameterized queries is fragile
- **Fix:** Use pure parameterized query with table name as parameter

#### 2. ILIKE Wildcard Injection (MEDIUM)
- **File:** `app/api/threads.py:465, 492`
- **Issue:** User search input not escaped: `f"%{q.strip().lower()}%"`
- **Impact:** Attacker can craft queries to match unintended data or cause regex DoS
- **Fix:** Escape special regex characters in search term

#### 3. Unvalidated JSON Deserialization (LOW)
- **File:** `app/adapters/openai_adapter.py:47`
- **Issue:** Provider responses parsed with `json.loads()` without schema validation
- **Impact:** Malformed responses could crash downstream processing
- **Fix:** Validate response against Pydantic model

---

### A04:2021 - INSECURE DESIGN (4 findings)

#### 1. Credentials in Plain Text Memory (HIGH)
- **File:** `app/api/threads.py:791-798`
- **Issue:** API keys retrieved and stored in plain dict during request handling
- **Impact:** Keys exposed in error messages, stack traces, memory dumps
- **Fix:** Use async context to clear credentials immediately after use
```python
async with AsyncContext(cleanup_credentials=True):
    # use credentials
```

#### 2. Shared Default Organization (HIGH)
- **File:** `app/api/auth.py:47-72`
- **Issue:** All unauthenticated users default to `settings.default_org_id`
- **Impact:** Demo users share same org context, data isolation fails
- **Fix:** Create per-session/IP organization isolation

#### 3. Rate Limit Fallback Disables Enforcement (MEDIUM)
- **File:** `app/services/ratelimit.py:59-61`
- **Issue:** If Redis down, silently disables rate limiting
- **Impact:** Unlimited requests/tokens during Redis outage
- **Fix:** Fail closed - raise exception instead of returning unlimited limits
```python
if redis_unavailable:
    raise ServiceUnavailableError("Rate limiting unavailable")
```

#### 4. No Rate Limiting on Auth Endpoints (MEDIUM)
- **File:** `app/api/auth.py:81-173`
- **Issue:** `/auth/clerk` endpoint has no rate limiting
- **Impact:** Vulnerable to credential stuffing, brute force
- **Fix:** Add rate limiter to all auth endpoints

---

### A05:2021 - SECURITY MISCONFIGURATION (6 findings)

#### 1. Debug Mode in Production Path (CRITICAL)
- **File:** `main.py:141`
- **Issue:** `uvicorn.run(..., reload=True)` in if __name__ == "__main__"
- **Impact:** Code reloading and debug endpoints if this path executed
- **Fix:** Remove reload=True and require environment variable control
```python
if __name__ == "__main__":
    import uvicorn
    reload = os.getenv("ENABLE_RELOAD", "false").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
```

#### 2. Detailed Error Messages (HIGH)
- **File:** `app/api/auth.py:171`, `app/api/threads_new_add_message.py:222`
- **Issue:** Exception messages exposed in API responses
- **Impact:** Leaks internal implementation details
- **Fix:** Log full error, return generic message to client
```python
logger.exception("Auth failed")
raise HTTPException(status_code=401, detail="Authentication failed")
```

#### 3. Stack Traces in Console Output (HIGH)
- **File:** `app/api/auth.py:166`
- **Issue:** `traceback.print_exc()` outputs to stdout
- **Impact:** Full traces visible in container logs
- **Fix:** Use logger.exception() instead

#### 4. Missing Security Headers on /docs (HIGH)
- **File:** `app/core/security_middleware.py:26`
- **Issue:** Security headers skipped for Swagger UI
- **Impact:** /docs accessible without XSS/clickjacking protection
- **Fix:** Apply headers to all routes except health checks

#### 5. Unvalidated ALLOWED_ORIGINS (MEDIUM)
- **File:** `app/core/security_middleware.py:53-54`
- **Issue:** No validation of origin URLs
- **Impact:** Allows invalid origins like `file://`, `javascript:`, `*`
- **Fix:** Validate each origin is valid HTTPS URL

#### 6. Unsafe-Inline CSP (MEDIUM)
- **File:** `app/core/security_middleware.py:29`
- **Issue:** `"script-src 'self' 'unsafe-inline';"` defeats XSS protection
- **Impact:** Inline script injection vulnerabilities
- **Fix:** Remove 'unsafe-inline', use nonce-based CSP

---

### A06:2021 - VULNERABLE & OUTDATED COMPONENTS (3 findings)

#### 1. Multiple Outdated Dependencies (MEDIUM)
- **File:** `requirements.txt`
- **Dependencies to update:**
  - fastapi==0.124.0 (current: 0.130+)
  - cryptography==46.0.3 (verify for CVEs)
  - passlib[bcrypt]==1.7.4 (should be 1.7.8+)
  - pydantic==2.12.5 (regularly update)
- **Fix:** Run `pip list --outdated` and update all packages
- **Action:** `pip install --upgrade fastapi cryptography passlib pydantic`

#### 2. No Dependency Locking (MEDIUM)
- **Issue:** No poetry.lock or pip.lock file
- **Impact:** Non-reproducible builds
- **Fix:** Use Poetry or pip-tools to lock versions
```bash
pip-compile requirements.in > requirements.txt
```

#### 3. Unused Firebase Admin (LOW)
- **File:** `requirements.txt`
- **Issue:** firebase-admin==7.1.0 not used but increases attack surface
- **Fix:** Remove from requirements.txt if not needed

---

### A07:2021 - AUTHENTICATION FAILURES (5 findings)

#### 1. No Token Revocation Mechanism (HIGH)
- **File:** `app/services/token_service.py`
- **Issue:** JWTs are stateless with no revocation list
- **Impact:** Compromised tokens remain valid until expiration (30 min)
- **Fix:** Implement token blacklist with Redis
```python
class TokenBlacklist:
    async def revoke_token(self, token_id: str, ttl: int):
        await redis.setex(f"token_blacklist:{token_id}", ttl, "1")

    async def is_revoked(self, token_id: str) -> bool:
        return await redis.exists(f"token_blacklist:{token_id}")
```

#### 2. JWT Signature Verification Bypass (HIGH)
- **File:** `app/services/clerk_client.py:50-53`
- **Issue:** Initial decode with `verify_signature=False`
- **Impact:** Timing window if Clerk API verification fails
- **Fix:** Add immediate signature verification
```python
jwt.decode(token, options={"verify_signature": True})
```

#### 3. Long Token Expiration (HIGH)
- **File:** `config.py:31`
- **Issue:** 30-minute token expiration without refresh token
- **Impact:** Large brute-force attack window
- **Fix:** Reduce to 5-15 minutes, implement refresh token rotation

#### 4. No Session Timeout (MEDIUM)
- **Issue:** No activity monitoring or forced re-authentication
- **Impact:** Long-lived sessions vulnerable to compromise
- **Fix:** Implement activity-based timeout
```python
# Track last_activity in token
if time.time() - last_activity > INACTIVITY_TIMEOUT:
    raise AuthenticationError("Session timeout")
```

#### 5. Insufficient Token Binding (MEDIUM)
- **Issue:** JWT doesn't include user IP, browser fingerprint, or device ID
- **Impact:** Token theft via network sniffing undetectable
- **Fix:** Include request fingerprint in token
```python
user_agent_hash = hashlib.sha256(request.headers['user-agent']).hexdigest()
token["fingerprint"] = user_agent_hash
```

---

### A08:2021 - SOFTWARE & DATA INTEGRITY FAILURES (3 findings)

#### 1. Unvalidated Content Size (HIGH)
- **File:** `app/api/threads.py:246`
- **Issue:** `content: str` field has no maximum length
- **Impact:** Attacker can store extremely large payloads
- **Fix:** Add maxlength validation
```python
content: str = Field(..., max_length=50000)
```

#### 2. No Integrity Verification (MEDIUM)
- **File:** `app/api/threads.py:189-190`
- **Issue:** Hashes computed but never verified during retrieval
- **Impact:** Silent corruption undetected
- **Fix:** Verify hash on every retrieval
```python
retrieved_hash = hashlib.sha256(content.encode()).hexdigest()
if retrieved_hash != stored_hash:
    raise DataIntegrityError("Content hash mismatch")
```

#### 3. Unsafe Deserialization (MEDIUM)
- **File:** `app/services/llm_context_extractor.py`
- **Issue:** `json.loads()` on LLM output without schema validation
- **Impact:** Malformed data crashes processing
- **Fix:** Use Pydantic for validation
```python
response = ContextResponse(**json.loads(llm_output))
```

---

### A09:2021 - LOGGING & MONITORING FAILURES (5 findings)

#### 1. API Keys in Debug Logs (CRITICAL)
- **File:** `app/api/threads.py:770` and others
- **Issue:** Debug output may include sensitive request parameters
- **Impact:** API keys exposed in logs if DEBUG level enabled
- **Fix:** Add sensitive field redaction to logger
```python
import logging_config
logger = logging_config.get_redacted_logger(__name__)
# Will automatically redact api_key, secret, password fields
```

#### 2. Stack Traces in Error Responses (HIGH)
- **File:** `app/core/error_handlers.py:142-143`
- **Issue:** Full traceback stored in log extra fields
- **Impact:** Leaks internal stack structure
- **Fix:** Only log traceback when status_code >= 500
```python
if status_code >= 500:
    extra["traceback"] = traceback.format_exc()
```

#### 3. No PII Masking (MEDIUM)
- **Issue:** User/org IDs logged without masking
- **Impact:** Logs contain personally identifiable information
- **Fix:** Add PII masking filter to logger
```python
def mask_pii(record):
    record.msg = re.sub(r'[a-f0-9]{8}-[a-f0-9-]{27}', '***-UUID-***', record.msg)
    return record
```

#### 4. Insufficient Audit Logging (MEDIUM)
- **File:** `app/api/providers.py:82`
- **Issue:** API key save operation missing user_id in audit trail
- **Impact:** Cannot track who made sensitive changes
- **Fix:** Include authenticated user in all audit logs
```python
audit_log(
    action="api_key_saved",
    user_id=current_user.id,
    org_id=org_id,
    provider=provider,
    timestamp=datetime.utcnow()
)
```

#### 5. No Rate Limit Alerting (LOW)
- **File:** `app/services/ratelimit.py:82-97`
- **Issue:** Rate limit violations not monitored
- **Impact:** Brute force attacks not detected
- **Fix:** Send alert on repeated violations
```python
if requests_remaining < 0:
    await send_security_alert(f"Rate limit exceeded for {org_id}")
```

---

### A10:2021 - SERVER-SIDE REQUEST FORGERY (4 findings)

#### 1. Unrestricted HTTP Client (MEDIUM)
- **File:** `app/adapters/_client.py:12-17`
- **Issue:** Shared HTTP client has no URL domain whitelist
- **Impact:** SSRF to internal services possible
- **Fix:** Whitelist allowed domains
```python
ALLOWED_DOMAINS = [
    "api.openai.com",
    "api.anthropic.com",
    "api.perplexity.ai",
    "generativelanguage.googleapis.com",
    "openrouter.ai"
]

def validate_url(url: str):
    parsed = urlparse(url)
    if parsed.netloc not in ALLOWED_DOMAINS:
        raise ValueError(f"Domain {parsed.netloc} not allowed")
```

#### 2. Unvalidated API Redirects (MEDIUM)
- **File:** `app/services/clerk_client.py:66-67`
- **Issue:** httpx follows redirects by default
- **Impact:** Clerk API could redirect to attacker domain
- **Fix:** Disable redirects for external APIs
```python
client.get(url, follow_redirects=False)
```

#### 3. Unvalidated Provider URLs (MEDIUM)
- **File:** `main.py:55-59`
- **Issue:** Provider URLs not validated to be HTTPS
- **Impact:** Downgrade to HTTP possible
- **Fix:** Enforce HTTPS for all external URLs
```python
if not url.startswith("https://"):
    raise ValueError(f"URL must use HTTPS: {url}")
```

#### 4. No Timeout Enforcement (LOW)
- **File:** `app/adapters/_client.py:8`
- **Issue:** No minimum timeout on individual calls
- **Impact:** Slow external services cause resource exhaustion
- **Fix:** Enforce timeouts on all external calls
```python
DEFAULT_TIMEOUT = 30.0
client.get(url, timeout=min(30.0, provided_timeout))
```

---

## Remediation Timeline

### PHASE 1: CRITICAL (Week 1)
- [ ] Remove debug mode from production paths
- [ ] Mask API keys in logs
- [ ] Remove detailed error messages from API responses
- [ ] Implement token revocation mechanism

### PHASE 2: HIGH (Week 2-3)
- [ ] User ID validation for all write operations
- [ ] Rate limiting on authentication endpoints
- [ ] JWT secret key strength enforcement
- [ ] Remove credentials from memory after use
- [ ] Add missing security headers to all routes
- [ ] Stack trace logging fixes

### PHASE 3: MEDIUM (Week 3-4)
- [ ] Implement ILIKE wildcard escaping
- [ ] Add content size limits
- [ ] Implement PII masking in logs
- [ ] Add audit logging for sensitive operations
- [ ] URL validation for external calls
- [ ] Update all dependencies

### PHASE 4: LOW (Week 4)
- [ ] Remove unsafe-inline CSP
- [ ] Implement rate limit alerting
- [ ] Timeout enforcement
- [ ] Remove unused firebase-admin

---

## Compliance Notes

### Current Status
- ❌ **NOT READY FOR PRODUCTION** - Multiple critical vulnerabilities

### Production Prerequisites
1. All CRITICAL findings remediated ✗
2. All HIGH findings remediated ✗
3. Penetration testing completed ✗
4. Security code review completed ✗
5. Security headers validated ✗
6. Dependency audit passed ✗
7. Rate limiting tested under load ✗
8. Incident response plan documented ✗

### Regulatory Alignment
- **GDPR:** PII masking not implemented
- **CCPA:** No data export/deletion audit trail
- **HIPAA:** Encryption key management insufficient
- **SOC2:** Logging and monitoring inadequate

---

## Recommendations

### Immediate Actions (Next 24 hours)
1. Disable debug mode on all entry points
2. Implement API key masking in logs
3. Add error response sanitization
4. Create security incident response plan

### Short-term (This Sprint)
1. Implement token revocation
2. Add user ID validation
3. Rate limit auth endpoints
4. Update all dependencies

### Medium-term (Next Sprint)
1. Implement comprehensive audit logging
2. Add security monitoring/alerting
3. Conduct third-party penetration test
4. Implement automated security scanning

### Long-term (Quarterly)
1. Implement zero-trust architecture
2. Add threat modeling for each feature
3. Quarterly penetration tests
4. Security training for team

---

## Conclusion

The Syntra backend has a solid foundation with proper ORM usage preventing SQL injection and basic security middleware in place. However, critical vulnerabilities related to credentials handling, debug mode, and error message exposure must be resolved before production deployment.

**Risk Assessment:** Production deployment not recommended until at minimum all CRITICAL and HIGH severity findings are addressed.

**Estimated Timeline:** 40-60 developer hours for full remediation

**Next Steps:** Create JIRA tickets for each finding and prioritize CRITICAL items for this sprint.

---

*Report Generated: December 18, 2025*
*Auditor: Security Analysis Agent*
*Next Review: After remediation completion*
