/**
 * Secrets Manager - Enterprise-grade secret retrieval abstraction
 *
 * Supports:
 * - EnvSecretManager: Local .env files (development)
 * - VaultSecretManager: HashiCorp Vault (production)
 * - AWSSecretManager: AWS Secrets Manager (production)
 *
 * Usage:
 *   import { getSecret, secretManager } from './secrets';
 *
 *   // Get a secret
 *   const jwtSecret = await getSecret('JWT_SECRET');
 *
 *   // Or use the manager directly
 *   const sm = secretManager();
 *   const dbPassword = await sm.getSecret('DATABASE_PASSWORD');
 *
 * Configuration:
 *   SECRET_BACKEND=env|vault|aws
 *   VAULT_ADDR, VAULT_TOKEN (for Vault)
 *   AWS_REGION, AWS_SECRET_PREFIX (for AWS)
 */

export interface SecretManager {
    getSecret(key: string, defaultValue?: string): Promise<string | undefined>;
    getSecrets(keys: string[]): Promise<Record<string, string | undefined>>;
    close(): Promise<void>;
}

/**
 * Environment-based secret manager for development.
 * Reads from process.env (populated by dotenv).
 *
 * WARNING: Not recommended for production.
 */
class EnvSecretManager implements SecretManager {
    constructor() {
        console.log('Using EnvSecretManager (development mode)');
    }

    async getSecret(key: string, defaultValue?: string): Promise<string | undefined> {
        return process.env[key] ?? defaultValue;
    }

    async getSecrets(keys: string[]): Promise<Record<string, string | undefined>> {
        const result: Record<string, string | undefined> = {};
        for (const key of keys) {
            result[key] = process.env[key];
        }
        return result;
    }

    async close(): Promise<void> {
        // No-op
    }
}

/**
 * HashiCorp Vault secret manager for production.
 *
 * Requires:
 *   npm install node-vault
 *
 * Environment:
 *   VAULT_ADDR: Vault server address
 *   VAULT_TOKEN: Authentication token
 *   VAULT_MOUNT: KV secrets engine mount point (default: "secret")
 *   VAULT_PATH: Path prefix for secrets (default: "beyondcloud")
 */
class VaultSecretManager implements SecretManager {
    private client: any;
    private mount: string;
    private path: string;
    private cache: Map<string, string> = new Map();

    constructor() {
        this.mount = process.env.VAULT_MOUNT || 'secret';
        this.path = process.env.VAULT_PATH || 'beyondcloud';
        console.log(`Using VaultSecretManager (mount=${this.mount}, path=${this.path})`);
    }

    private async getClient(): Promise<any> {
        if (!this.client) {
            try {
                // Dynamic import for optional dependency
                const vault = await import('node-vault');
                const vaultAddr = process.env.VAULT_ADDR;
                const vaultToken = process.env.VAULT_TOKEN;

                if (!vaultAddr) {
                    throw new Error('VAULT_ADDR environment variable required');
                }

                this.client = vault.default({
                    apiVersion: 'v1',
                    endpoint: vaultAddr,
                    token: vaultToken,
                });

                console.log(`Connected to Vault at ${vaultAddr}`);
            } catch (error: any) {
                if (error.code === 'MODULE_NOT_FOUND') {
                    throw new Error(
                        'node-vault package required for Vault integration. ' +
                        'Install with: npm install node-vault'
                    );
                }
                throw error;
            }
        }
        return this.client;
    }

    async getSecret(key: string, defaultValue?: string): Promise<string | undefined> {
        // Check cache first
        if (this.cache.has(key)) {
            return this.cache.get(key);
        }

        try {
            const client = await this.getClient();
            const secretPath = `${this.mount}/data/${this.path}/${key}`;
            const response = await client.read(secretPath);
            const value = response?.data?.data?.value ?? defaultValue;

            if (value) {
                this.cache.set(key, value);
            }
            return value;
        } catch (error: any) {
            console.warn(`Failed to get secret '${key}' from Vault: ${error.message}`);
            return defaultValue;
        }
    }

    async getSecrets(keys: string[]): Promise<Record<string, string | undefined>> {
        const result: Record<string, string | undefined> = {};
        for (const key of keys) {
            result[key] = await this.getSecret(key);
        }
        return result;
    }

    async close(): Promise<void> {
        this.client = null;
        this.cache.clear();
    }
}

/**
 * AWS Secrets Manager for production.
 *
 * Requires:
 *   npm install @aws-sdk/client-secrets-manager
 *
 * Environment:
 *   AWS_REGION: AWS region (default: us-east-1)
 *   AWS_SECRET_PREFIX: Prefix for secret names (default: "beyondcloud/")
 *
 * Authentication via standard AWS credentials chain.
 */
class AWSSecretManager implements SecretManager {
    private client: any;
    private region: string;
    private prefix: string;
    private cache: Map<string, string> = new Map();

    constructor() {
        this.region = process.env.AWS_REGION || 'us-east-1';
        this.prefix = process.env.AWS_SECRET_PREFIX || 'beyondcloud/';
        console.log(`Using AWSSecretManager (region=${this.region}, prefix=${this.prefix})`);
    }

    private async getClient(): Promise<any> {
        if (!this.client) {
            try {
                const { SecretsManagerClient } = await import('@aws-sdk/client-secrets-manager');
                this.client = new SecretsManagerClient({ region: this.region });
                console.log(`Connected to AWS Secrets Manager in ${this.region}`);
            } catch (error: any) {
                if (error.code === 'MODULE_NOT_FOUND') {
                    throw new Error(
                        '@aws-sdk/client-secrets-manager package required. ' +
                        'Install with: npm install @aws-sdk/client-secrets-manager'
                    );
                }
                throw error;
            }
        }
        return this.client;
    }

    async getSecret(key: string, defaultValue?: string): Promise<string | undefined> {
        // Check cache first
        if (this.cache.has(key)) {
            return this.cache.get(key);
        }

        try {
            const { GetSecretValueCommand } = await import('@aws-sdk/client-secrets-manager');
            const client = await this.getClient();
            const secretName = `${this.prefix}${key}`;

            const response = await client.send(
                new GetSecretValueCommand({ SecretId: secretName })
            );

            let value: string | undefined;
            if (response.SecretString) {
                // Try to parse as JSON
                try {
                    const parsed = JSON.parse(response.SecretString);
                    value = parsed.value ?? response.SecretString;
                } catch {
                    value = response.SecretString;
                }
            } else if (response.SecretBinary) {
                value = Buffer.from(response.SecretBinary).toString('utf-8');
            }

            if (value) {
                this.cache.set(key, value);
            }
            return value ?? defaultValue;
        } catch (error: any) {
            console.warn(`Failed to get secret '${key}' from AWS: ${error.message}`);
            return defaultValue;
        }
    }

    async getSecrets(keys: string[]): Promise<Record<string, string | undefined>> {
        const result: Record<string, string | undefined> = {};
        for (const key of keys) {
            result[key] = await this.getSecret(key);
        }
        return result;
    }

    async close(): Promise<void> {
        this.client = null;
        this.cache.clear();
    }
}

// =============================================================================
// Factory and Global Instance
// =============================================================================

let _secretManager: SecretManager | null = null;

/**
 * Get or create the global secret manager instance.
 *
 * Backend selection via SECRET_BACKEND environment variable:
 *   - "env" (default): Environment variables
 *   - "vault": HashiCorp Vault
 *   - "aws": AWS Secrets Manager
 */
export function secretManager(): SecretManager {
    if (!_secretManager) {
        const backend = (process.env.SECRET_BACKEND || 'env').toLowerCase();

        switch (backend) {
            case 'vault':
                _secretManager = new VaultSecretManager();
                break;
            case 'aws':
                _secretManager = new AWSSecretManager();
                break;
            default:
                _secretManager = new EnvSecretManager();
        }
    }
    return _secretManager;
}

/**
 * Convenience function to get a secret
 */
export async function getSecret(key: string, defaultValue?: string): Promise<string | undefined> {
    return secretManager().getSecret(key, defaultValue);
}

/**
 * Convenience function to get multiple secrets
 */
export async function getSecrets(keys: string[]): Promise<Record<string, string | undefined>> {
    return secretManager().getSecrets(keys);
}
