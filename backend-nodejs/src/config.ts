import dotenv from 'dotenv';
import path from 'path';

// Load .env file
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

export const config = {
    // Server
    port: parseInt(process.env.PORT || '3000', 10),
    nodeEnv: process.env.NODE_ENV || 'development',

    // Database (for later phases)
    databaseUrl: process.env.DATABASE_URL || 'postgresql://localhost:5432/llamacpp_chat',

    // JWT (for later phases)
    jwtSecret: process.env.JWT_SECRET || 'change-this-in-production',
    jwtAlgorithm: process.env.JWT_ALGORITHM || 'HS256',
    accessTokenExpireMinutes: parseInt(process.env.ACCESS_TOKEN_EXPIRE_MINUTES || '15', 10),
    refreshTokenExpireDays: parseInt(process.env.REFRESH_TOKEN_EXPIRE_DAYS || '7', 10),

    // Frontend URL (for CORS)
    frontendUrl: process.env.FRONTEND_URL || 'http://localhost:5173',

    // LLM Providers
    defaultLlmProvider: process.env.DEFAULT_LLM_PROVIDER || 'llama.cpp',

    // Provider URLs (can be overridden via env)
    providers: {
        'llama.cpp': {
            baseUrl: process.env.LLAMA_CPP_URL || 'http://localhost:8080/v1',
        },
        'ollama': {
            baseUrl: process.env.OLLAMA_URL || 'http://localhost:11434/v1',
        },
        'openai': {
            baseUrl: process.env.OPENAI_URL || 'https://api.openai.com/v1',
            apiKey: process.env.OPENAI_API_KEY,
        },
        'gemini': {
            baseUrl: process.env.GEMINI_URL || 'https://generativelanguage.googleapis.com/v1beta/openai',
            apiKey: process.env.GEMINI_API_KEY,
        },
        'groq': {
            baseUrl: process.env.GROQ_URL || 'https://api.groq.com/openai/v1',
            apiKey: process.env.GROQ_API_KEY,
        },
    },
} as const;

export type Config = typeof config;
