# Node.js/Express Backend

Implementation of the llama.cpp Authenticated WebUI backend using Node.js and Express.

## Quick Start

```bash
cd backend-nodejs
npm install
cp .env.example .env
# Edit .env with your configuration
npm run dev
```

## API Contract

This backend implements the exact same API as `backend-python`.  
See [api-contract.md](../docs/api-contract.md) for complete specification.

## Project Structure

```
backend-nodejs/
├── src/
│   ├── index.ts           # Express app entry point
│   ├── config.ts          # Settings & configuration
│   ├── database.ts        # PostgreSQL connection (pg/TypeORM)
│   ├── models/            # TypeORM entities
│   │   ├── User.ts
│   │   ├── Conversation.ts
│   │   ├── Message.ts
│   │   └── Token.ts
│   ├── types/             # TypeScript interfaces
│   │   ├── auth.ts
│   │   ├── conversation.ts
│   │   └── message.ts
│   ├── routes/            # Express routes
│   │   ├── auth.ts
│   │   ├── conversations.ts
│   │   ├── messages.ts
│   │   ├── chat.ts
│   │   ├── settings.ts
│   │   └── mcp.ts         # Placeholder
│   ├── services/          # Business logic
│   │   ├── authService.ts
│   │   ├── llmRouter.ts
│   │   └── mcpService.ts  # Placeholder
│   ├── middleware/
│   │   ├── auth.ts        # JWT verification
│   │   ├── rateLimiter.ts
│   │   └── errorHandler.ts
│   └── utils/
│       ├── jwt.ts
│       ├── password.ts
│       └── email.ts
├── package.json
├── tsconfig.json
├── .env.example
└── tests/
    └── ...
```

## Dependencies

- **express** - Web framework
- **typescript** - Type safety
- **typeorm** - ORM
- **pg** - PostgreSQL driver
- **jsonwebtoken** - JWT handling
- **bcrypt** - Password hashing
- **zod** - Validation
- **helmet** - Security headers
- **cors** - CORS handling
- **nodemailer** - Email sending

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/llamacpp_chat
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
FRONTEND_URL=http://localhost:5173
PORT=3000
```

## Scripts

```bash
npm run dev      # Development with hot reload
npm run build    # Build TypeScript
npm start        # Production
npm test         # Run tests
```
