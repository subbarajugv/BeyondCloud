import { Pool, PoolClient } from 'pg';
import { config } from '../config';

// Create connection pool
const pool = new Pool({
    connectionString: config.databaseUrl,
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
});

// Log connection events
pool.on('connect', () => {
    console.log('Database: New client connected');
});

pool.on('error', (err) => {
    console.error('Database: Unexpected error on idle client', err);
});

/**
 * Execute a query
 */
export async function query<T = any>(text: string, params?: any[]): Promise<T[]> {
    const start = Date.now();
    const result = await pool.query(text, params);
    const duration = Date.now() - start;

    if (duration > 100) {
        console.log('Database: Slow query', { text: text.substring(0, 50), duration, rows: result.rowCount });
    }

    return result.rows as T[];
}

/**
 * Get a client from the pool for transactions
 */
export async function getClient(): Promise<PoolClient> {
    return pool.connect();
}

/**
 * Test database connection
 */
export async function testConnection(): Promise<boolean> {
    try {
        await pool.query('SELECT NOW()');
        console.log('Database: Connection successful');
        return true;
    } catch (error) {
        console.error('Database: Connection failed', error);
        return false;
    }
}

/**
 * Initialize database (create tables if not exist)
 */
export async function initializeDatabase(): Promise<void> {
    const fs = await import('fs');
    const path = await import('path');

    try {
        const schemaPath = path.join(__dirname, 'schema.sql');
        const schema = fs.readFileSync(schemaPath, 'utf-8');
        await pool.query(schema);
        console.log('Database: Schema initialized');
    } catch (error) {
        console.error('Database: Schema initialization failed', error);
        throw error;
    }
}

/**
 * Close pool connections
 */
export async function closePool(): Promise<void> {
    await pool.end();
    console.log('Database: Pool closed');
}

export { pool };
