# Issues Fixed - January 2026

## ✅ 1. Vector Search Error (FIXED)

**Error**: `agent.tools - ERROR - Vector search failed: 'chunk_id'`

**Root Cause**: 
- LanceDB returns results with `id` field, not `chunk_id`
- Code was trying to access `chunk_id` which doesn't exist
- Metadata is already parsed as dict, not JSON string

**Fix Applied**:
- Updated `agent/tools.py` to safely extract `id` field (not `chunk_id`)
- Added defensive error handling with try/except for each result
- Properly handle metadata as dict (already parsed by db_utils)
- Convert `_distance` to similarity score correctly

**Files Changed**:
- `yukio/agent/tools.py` - `vector_search_tool()` and `hybrid_search_tool()`

**Testing**:
```bash
cd yukio
source .venv/bin/activate
python scripts/diagnose_schema.py  # Confirms schema
```

---

## 🔍 2. Why CLI Works Better Than Frontend Chat

**Key Differences**:

1. **Error Handling**:
   - CLI: Better error messages and graceful degradation
   - Frontend: May fail silently or show generic errors

2. **Connection Stability**:
   - CLI: Direct connection to backend, no proxy issues
   - Frontend: Goes through Next.js rewrites (`/api/backend/*`)

3. **Streaming**:
   - CLI: Handles streaming responses more reliably
   - Frontend: May have issues with WebSocket/SSE connections

4. **Error Recovery**:
   - CLI: Can retry and show detailed error messages
   - Frontend: Limited error context in browser console

**Recommendations**:
- Frontend should add better error handling and retry logic
- Add connection status indicator in frontend
- Improve error messages for users

---

## ⚠️ 3. Mem0 Not Installed (Optional)

**Status**: Optional dependency - not critical for basic functionality

**Fix** (if needed):
```bash
cd yukio
source .venv/bin/activate
pip install mem0ai
```

**Note**: Mem0 is used for advanced memory features. The system works without it using LanceDB for memory.

---

## ⚠️ 4. TTS Slow on Apple Silicon (Known Issue)

**Status**: Known limitation - Dia TTS is not optimized for M1/M2/M3

**Options**:
1. **Disable TTS** (Recommended for development):
   ```bash
   export YUKIO_DISABLE_TTS=1
   uvicorn agent.api:app --reload --port 8058
   ```

2. **Use macOS Native TTS** (Fast but less natural):
   - Would require code changes to use `say` command
   - Japanese voice: `say -v Kyoko "こんにちは"`

3. **Wait for MLX-Audio** (Future):
   - MLX-Audio is optimized for Apple Silicon
   - Not yet integrated

**Current Behavior**:
- TTS works but takes 2-5 minutes per response on Apple Silicon
- CLI automatically disables voice on Apple Silicon
- Frontend should show warning or disable TTS button

---

## ⚠️ 5. Font Loading (Minor)

**Error**: `request to fonts.gstatic.com failed, reason: getaddrinfo ENOTFOUND`

**Status**: Network/DNS issue - not critical

**Fix** (if needed):
- Use `display: 'swap'` in Next.js font config
- Or use local fonts instead of Google Fonts

**Impact**: Low - fonts will fallback to system fonts

---

## 📊 Summary

| Issue | Priority | Status | Impact |
|-------|----------|--------|--------|
| Vector search `'chunk_id'` | 🔴 Critical | ✅ Fixed | High - Blocks RAG |
| CLI vs Frontend | 🟡 Medium | 📝 Documented | Medium - UX issue |
| Mem0 not installed | 🟢 Low | Optional | Low - Feature enhancement |
| TTS slow on M1/M2 | 🟡 Medium | Known | Medium - Performance |
| Font loading | 🟢 Low | Minor | Low - Cosmetic |

---

## 🚀 Next Steps

1. ✅ **Vector search fixed** - Test with frontend chat
2. 📝 **Improve frontend error handling** - Add retry logic and better error messages
3. 🔧 **Optimize TTS** - Consider macOS native TTS or disable by default on Apple Silicon
4. 📊 **Monitor performance** - Check if vector search errors are resolved

---

## 🧪 Testing

Test the vector search fix:
```bash
# Backend
cd yukio
source .venv/bin/activate
uvicorn agent.api:app --reload --port 8058

# Frontend (in another terminal)
cd yukio-frontend
npm run dev

# Test chat in frontend - should work without vector search errors
```

Check logs for:
- ✅ No more `'chunk_id'` errors
- ✅ Vector search returns results
- ✅ RAG agent can generate responses

