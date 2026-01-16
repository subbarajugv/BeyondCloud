# Removing IndexedDB/Dexie (Optional)

The app currently uses a **hybrid storage approach**:
- **Authenticated users** → Backend API (PostgreSQL)
- **Unauthenticated users** → IndexedDB (Dexie)
- **API failures** → Falls back to IndexedDB

## When to Remove

Remove Dexie if you want to:
- Force all users to register
- Eliminate offline/guest mode
- Reduce bundle size (~50KB)

## How to Remove

### 1. Modify `database.ts`

Remove the Dexie import and class:
```diff
- import Dexie, { type EntityTable } from 'dexie';
- 
- class LlamacppDatabase extends Dexie { ... }
- const db = new LlamacppDatabase();
```

Remove `useApiStorage()` checks - always use API:
```diff
- if (useApiStorage()) {
-   // API code
- } else {
-   // Dexie code
- }
+ // Just API code directly
```

Remove all IndexedDB fallback branches.

### 2. Remove Dependency

```bash
cd frontend
npm uninstall dexie
```

### 3. Update Auth Flow

Force login by updating `+layout.svelte` to redirect unauthenticated users.

## Debugging Tips

If removed and issues occur:

1. **Check API calls** - Network tab → filter by `/api/`
2. **Auth token** - `localStorage.getItem('auth_token')` in console
3. **API errors** - Backend logs show detailed errors
4. **Clear old data** - `indexedDB.deleteDatabase('LlamacppWebui')`

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/lib/stores/database.ts` | Remove Dexie, use API only |
| `frontend/src/routes/+layout.svelte` | Add auth redirect |
| `frontend/package.json` | Remove dexie dependency |

## Estimated Effort

~1-2 hours for complete removal and testing.
