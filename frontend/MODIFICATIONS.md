# Frontend Modifications Guide

This is a copy of the llama.cpp WebUI. To add authentication, you'll need to make the following modifications:

## Files to Create

### 1. Authentication Store
**File:** `src/lib/stores/auth.svelte.ts`

Create a new store to manage authentication state:
- User information
- JWT token
- Login/logout methods
- Token refresh logic

### 2. API Client Service
**File:** `src/lib/services/api.ts`

Centralized API client for backend communication:
- Automatic JWT token injection
- Error handling
- Request/response interceptors

### 3. Login Page
**File:** `src/routes/login/+page.svelte`

User login interface with:
- Email/password form
- Error handling
- Redirect after successful login

### 4. Register Page
**File:** `src/routes/register/+page.svelte`

User registration interface with:
- Email/password form
- Password confirmation
- Validation
- Redirect to login after registration

### 5. Auth Components
**Files:**
- `src/lib/components/auth/LoginForm.svelte`
- `src/lib/components/auth/RegisterForm.svelte`
- `src/lib/components/auth/UserProfile.svelte`

Reusable authentication UI components.

## Files to Modify

### 1. Root Layout
**File:** `src/routes/+layout.svelte`

Add authentication check and route protection:
```svelte
<script lang="ts">
  import { authStore } from '$lib/stores/auth.svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  // Check authentication on mount
  $effect(() => {
    authStore.checkAuth();
  });

  // Redirect logic
  $effect(() => {
    const publicRoutes = ['/login', '/register'];
    const isPublicRoute = publicRoutes.includes(page.route.id || '');
    
    if (!authStore.isAuthenticated && !isPublicRoute) {
      goto('/login');
    } else if (authStore.isAuthenticated && isPublicRoute) {
      goto('/');
    }
  });
</script>
```

### 2. Database Store
**File:** `src/lib/stores/database.ts`

Replace IndexedDB operations with API calls:
- Remove Dexie dependency
- Replace all `db.conversations.add()` with `apiClient.post('/api/conversations')`
- Replace all `db.messages.add()` with `apiClient.post('/api/messages')`
- Add error handling for network failures

### 3. Chat Service
**File:** `src/lib/services/chat.ts`

Update API endpoints to use authenticated backend:
```typescript
// Before
fetch(`./v1/chat/completions`, {
  headers: { Authorization: `Bearer ${apiKey}` }
})

// After
fetch(`/api/chat/completions`, {
  headers: { Authorization: `Bearer ${authStore.token}` }
})
```

### 4. Settings Store
**File:** `src/lib/stores/settings.svelte.ts`

Sync settings with backend instead of localStorage:
```typescript
// Before
localStorage.setItem('config', JSON.stringify(this.config))

// After
await apiClient.put('/api/settings', this.config)
```

### 5. Chat Store
**File:** `src/lib/stores/chat.svelte.ts`

Update to use API-based storage:
- Replace `DatabaseStore.createConversation()` with API calls
- Replace `DatabaseStore.createMessage()` with API calls
- Update conversation loading logic

## Configuration Changes

### 1. Vite Config
**File:** `vite.config.ts`

Add API proxy for development:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  }
});
```

### 2. Environment Variables
**File:** `.env`

```env
PUBLIC_API_URL=http://localhost:3000/api
```

## Dependencies to Add

```bash
# No new dependencies needed!
# The existing stack already has everything we need
```

## Dependencies to Remove (After Migration)

```bash
npm uninstall dexie
```

## Development Workflow

1. **Start Backend** (in separate terminal):
   ```bash
   cd ../backend
   npm run dev  # or python main.py, or go run main.go
   ```

2. **Start Frontend**:
   ```bash
   npm run dev
   ```

3. **Access Application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:3000
   - llama.cpp: http://localhost:8080

## Testing Checklist

- [ ] Can register new user
- [ ] Can login with credentials
- [ ] Redirects to login when not authenticated
- [ ] Can create conversation after login
- [ ] Can send messages
- [ ] Can logout
- [ ] Token persists across page refresh
- [ ] Multiple users have isolated data

## Migration Notes

If you have existing chat data in IndexedDB, create a migration tool:
1. Export IndexedDB data to JSON
2. POST to `/api/conversations/import` endpoint
3. Clear local IndexedDB after successful import

See `../docs/implementation_plan.md` for detailed migration strategy.
