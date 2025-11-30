# Phase 1 Smoke Test Checklist

**Date:** _______________  
**Tester:** _______________  
**Environment:** Local Development

---

## Pre-Test Setup

- [ ] Docker services running (Postgres, Redis, Qdrant)
- [ ] Backend API running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] Browser console open (F12 → Console tab)

---

## Step 1: App Launch & Visual Sanity Check

### 1.1 Launch App
- [ ] Navigate to http://localhost:3000
- [ ] Page loads without blank screen
- [ ] No red errors in browser console
- [ ] Header/navigation visible

**Expected:** Clean page load, no console errors  
**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 1.2 Visual Layout
- [ ] Header renders correctly (DAC logo, navigation links)
- [ ] Dark theme applied consistently
- [ ] Responsive layout (test mobile view in DevTools)
- [ ] No overlapping elements or broken layouts

**Expected:** Clean, responsive UI matching design  
**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 2: Navigation Test

### 2.1 Home Page
- [ ] Navigate to `/` (home page)
- [ ] Hero section visible
- [ ] Features section renders
- [ ] Footer visible

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 2.2 Threads Page
- [ ] Click "Threads" in header (or navigate to `/threads`)
- [ ] Page loads without 404
- [ ] Thread interface visible
- [ ] Scope toggle visible (Private only / Allow shared)
- [ ] Message input field visible

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 2.3 Settings Page
- [ ] Click "Settings" in header (or navigate to `/settings/providers`)
- [ ] Page loads without 404
- [ ] Provider cards visible (Perplexity, OpenAI, Gemini, OpenRouter)
- [ ] Memory status section visible

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 3: Core Feature Test - Threads

### 3.1 Create Thread & Send Message
- [ ] Type a message in the input field (e.g., "What is AI?")
- [ ] Click Send button
- [ ] User message appears in chat
- [ ] Loading indicator shows ("Thinking...")
- [ ] Assistant response appears
- [ ] Provider badge visible on assistant message
- [ ] Router reason visible (e.g., "web_search", "structured_output")

**Expected:** Full message flow works, provider selected automatically  
**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 3.2 Provider Badge Display
- [ ] Provider badge shows correct provider name (Perplexity/OpenAI/Gemini/OpenRouter)
- [ ] Badge has correct color coding
- [ ] Router reasoning displayed

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 3.3 Scope Toggle
- [ ] Toggle "Forward Scope" switch
- [ ] Switch changes from "Private only" to "Allow shared"
- [ ] Scope persists when sending next message

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 3.4 Message Copying
- [ ] Hover over a message
- [ ] Copy button appears
- [ ] Click copy button
- [ ] Message copied to clipboard (verify by pasting)

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 4: Core Feature Test - Settings

### 4.1 Provider Status Display
- [ ] Navigate to `/settings/providers`
- [ ] All 4 providers visible (Perplexity, OpenAI, Gemini, OpenRouter)
- [ ] Each provider shows "Configured" badge if key exists
- [ ] Memory status section visible

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 4.2 Add API Key
- [ ] Click "Add Key" on a provider (e.g., OpenAI)
- [ ] Input fields appear (API Key, Key Name)
- [ ] Enter a test API key
- [ ] Click "Save"
- [ ] Success: Key saved, form resets
- [ ] Provider shows "Configured" badge

**Expected:** Key saves successfully, status updates  
**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 4.3 Test Connection
- [ ] Click "Test" button on a configured provider
- [ ] Loading indicator shows
- [ ] Test result appears (success/failure message)
- [ ] Success: Green checkmark and message
- [ ] Failure: Red X and error message

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 4.4 Usage Statistics
- [ ] If provider is configured and used, usage stats visible
- [ ] Shows "Requests Today: X / Y"
- [ ] Shows "Tokens Today: X / Y"

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 5: Error Handling

### 5.1 Rate Limit Handling
- [ ] Send multiple messages rapidly (if rate limit configured)
- [ ] Rate limit error message appears (429)
- [ ] Error message is user-friendly
- [ ] App doesn't crash

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 5.2 Network Error Handling
- [ ] Stop backend server
- [ ] Try to send a message
- [ ] Error message appears
- [ ] App doesn't crash

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 5.3 Invalid Input
- [ ] Try to save API key with empty field
- [ ] Form validation prevents submission
- [ ] Error message appears

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 6: Network & API Verification

### 6.1 API Requests
- [ ] Open DevTools → Network tab
- [ ] Send a message in threads
- [ ] Verify API calls:
  - `POST /api/threads/` (create thread)
  - `POST /api/router/choose` (router decision)
  - `POST /api/threads/{id}/messages` (send message)
- [ ] All requests return status 200 (or expected status)
- [ ] `x-org-id` header present in all requests

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 6.2 Provider Status API
- [ ] Navigate to settings page
- [ ] Check Network tab
- [ ] `GET /api/orgs/{org_id}/providers/status` called
- [ ] Response contains provider statuses and memory status

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 7: Performance & Reload

### 7.1 Page Reload
- [ ] Reload the page (F5)
- [ ] App reloads cleanly
- [ ] No double errors in console
- [ ] State resets appropriately (messages clear, which is expected)

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

### 7.2 Console Cleanup
- [ ] Check browser console (F12 → Console)
- [ ] No red errors
- [ ] Only warnings or info messages (acceptable)
- [ ] Log any errors found

**Status:** ⬜ Pass / ⬜ Fail  
**Errors Found:** _________________________________

---

## Step 8: Mobile Responsiveness

### 8.1 Mobile View
- [ ] Open DevTools → Toggle device toolbar (Ctrl+Shift+M)
- [ ] Select mobile device (e.g., iPhone 12)
- [ ] Navigate through all pages
- [ ] Layout adjusts correctly
- [ ] All buttons/inputs accessible
- [ ] No horizontal scrolling

**Status:** ⬜ Pass / ⬜ Fail  
**Notes:** _________________________________

---

## Step 9: Final Verification

### 9.1 Backend Health
- [ ] Check http://localhost:8000/health
- [ ] Returns `{"status":"healthy"}`

**Status:** ⬜ Pass / ⬜ Fail  

### 9.2 Docker Services
- [ ] Postgres: Healthy
- [ ] Redis: Healthy
- [ ] Qdrant: Running (unhealthy is OK for Phase 1)

**Status:** ⬜ Pass / ⬜ Fail  

---

## Test Results Summary

| Test Category | Pass/Fail | Notes |
|--------------|-----------|-------|
| App Launch | ⬜ | |
| Visual Layout | ⬜ | |
| Navigation | ⬜ | |
| Threads - Send Message | ⬜ | |
| Threads - Provider Badge | ⬜ | |
| Threads - Scope Toggle | ⬜ | |
| Settings - Provider Status | ⬜ | |
| Settings - Add Key | ⬜ | |
| Settings - Test Connection | ⬜ | |
| Error Handling | ⬜ | |
| API Integration | ⬜ | |
| Performance | ⬜ | |
| Mobile Responsive | ⬜ | |

---

## Overall Result

**Phase 1 Smoke Test:** ⬜ **PASS** / ⬜ **FAIL**

### Critical Blockers (if any):
1. _________________________________
2. _________________________________
3. _________________________________

### Minor Issues (non-blocking):
1. _________________________________
2. _________________________________

### Notes:
_________________________________
_________________________________
_________________________________

---

## Next Steps

- [ ] If PASS: Proceed to Phase 2 or deeper testing
- [ ] If FAIL: Document blockers, create tickets, fix before proceeding

---

**Test Completed By:** _______________  
**Date:** _______________









