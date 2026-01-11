import { Router, Response } from 'express';
import { query, getClient } from '../db';
import { authenticateToken, AuthenticatedRequest } from '../middleware/auth';

const router = Router();

// All conversation routes require authentication
router.use(authenticateToken);

interface Message {
    id: string;
    parent_id: string | null;
    role: string;
    content: string;
    model: string | null;
    provider: string | null;
    reasoning_content: string | null;
    created_at: Date;
    children?: string[]; // Populated in application layer if needed, or by client
}

interface Conversation {
    id: string;
    name: string | null;
    current_node: string | null;
    created_at: Date;
    updated_at: Date;
    message_count?: number;
    last_message?: string;
}

/**
 * GET /api/conversations
 * List all conversations for the current user
 */
router.get('/', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    try {
        const conversations = await query<Conversation & { message_count: number; last_message: string }>(
            `SELECT 
                c.id, c.name, c.current_node, c.created_at, c.updated_at,
                COUNT(m.id)::int as message_count,
                (SELECT content FROM messages 
                 WHERE conversation_id = c.id 
                 ORDER BY created_at DESC LIMIT 1) as last_message
             FROM conversations c
             LEFT JOIN messages m ON m.conversation_id = c.id
             WHERE c.user_id = $1
             GROUP BY c.id
             ORDER BY c.updated_at DESC`,
            [req.user.id]
        );

        res.json({ conversations });
    } catch (error) {
        console.error('Error listing conversations:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to list conversations' },
        });
    }
});

/**
 * POST /api/conversations
 * Create a new conversation
 */
router.post('/', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { name } = req.body;

    try {
        const conversations = await query<Conversation>(
            `INSERT INTO conversations (user_id, name)
             VALUES ($1, $2)
             RETURNING id, name, current_node, created_at, updated_at`,
            [req.user.id, name || null]
        );

        res.status(201).json({ conversation: conversations[0] });
    } catch (error) {
        console.error('Error creating conversation:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to create conversation' },
        });
    }
});

/**
 * GET /api/conversations/:id
 * Get a conversation with all its messages
 */
router.get('/:id', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { id } = req.params;

    try {
        // Get conversation (verify ownership)
        const conversations = await query<Conversation>(
            `SELECT id, name, current_node, created_at, updated_at
             FROM conversations
             WHERE id = $1 AND user_id = $2`,
            [id, req.user.id]
        );

        if (conversations.length === 0) {
            return res.status(404).json({
                error: { code: 'NOT_FOUND', message: 'Conversation not found' },
            });
        }

        // Get messages
        const messages = await query<Message>(
            `SELECT id, parent_id, role, content, model, provider, reasoning_content, created_at
             FROM messages
             WHERE conversation_id = $1
             ORDER BY created_at ASC`,
            [id]
        );

        res.json({
            conversation: conversations[0],
            messages,
        });
    } catch (error) {
        console.error('Error getting conversation:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to get conversation' },
        });
    }
});

/**
 * PUT /api/conversations/:id
 * Update conversation name or current_node
 */
router.put('/:id', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { id } = req.params;
    const { name, current_node } = req.body;

    // Build update query dynamically
    const updates: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (name !== undefined) {
        updates.push(`name = $${paramIndex++}`);
        values.push(name);
    }
    if (current_node !== undefined) {
        updates.push(`current_node = $${paramIndex++}`);
        values.push(current_node);
    }

    if (updates.length === 0) {
        return res.status(400).json({
            error: { code: 'VALIDATION_ERROR', message: 'No fields to update' },
        });
    }

    values.push(id);
    values.push(req.user.id);

    try {
        const conversations = await query<Conversation>(
            `UPDATE conversations
             SET ${updates.join(', ')}
             WHERE id = $${paramIndex++} AND user_id = $${paramIndex++}
             RETURNING id, name, current_node, created_at, updated_at`,
            values
        );

        if (conversations.length === 0) {
            return res.status(404).json({
                error: { code: 'NOT_FOUND', message: 'Conversation not found' },
            });
        }

        res.json({ conversation: conversations[0] });
    } catch (error) {
        console.error('Error updating conversation:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to update conversation' },
        });
    }
});

/**
 * DELETE /api/conversations/:id
 * Delete a conversation and all its messages
 */
router.delete('/:id', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { id } = req.params;

    try {
        const result = await query(
            `DELETE FROM conversations
             WHERE id = $1 AND user_id = $2
             RETURNING id`,
            [id, req.user.id]
        );

        if (result.length === 0) {
            return res.status(404).json({
                error: { code: 'NOT_FOUND', message: 'Conversation not found' },
            });
        }

        res.json({ success: true });
    } catch (error) {
        console.error('Error deleting conversation:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to delete conversation' },
        });
    }
});

/**
 * POST /api/conversations/:id/messages
 * Add a message to a conversation
 */
router.post('/:id/messages', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { id } = req.params;
    const { role, content, model, provider, reasoningContent, parentId } = req.body;

    if (!role || !content) {
        return res.status(400).json({
            error: { code: 'VALIDATION_ERROR', message: 'Role and content are required' },
        });
    }

    const client = await getClient();

    try {
        await client.query('BEGIN');

        // Verify conversation ownership
        const conversations = await client.query(
            `SELECT id FROM conversations WHERE id = $1 AND user_id = $2`,
            [id, req.user.id]
        );

        if (conversations.rows.length === 0) {
            await client.query('ROLLBACK');
            return res.status(404).json({
                error: { code: 'NOT_FOUND', message: 'Conversation not found' },
            });
        }

        // Insert message
        const messages = await client.query<Message>(
            `INSERT INTO messages (conversation_id, role, content, model, provider, reasoning_content, parent_id)
             VALUES ($1, $2, $3, $4, $5, $6, $7)
             RETURNING id, parent_id, role, content, model, provider, reasoning_content, created_at`,
            [id, role, content, model || null, provider || null, reasoningContent || null, parentId || null]
        );

        const newMessage = messages.rows[0];

        // Update conversation updated_at AND current_node (auto-advance branch tip)
        await client.query(
            `UPDATE conversations 
             SET updated_at = NOW(), current_node = $1
             WHERE id = $2`,
            [newMessage.id, id]
        );

        await client.query('COMMIT');

        res.status(201).json({ message: newMessage });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('Error adding message:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to add message' },
        });
    } finally {
        client.release();
    }
});

/**
 * POST /api/conversations/:id/messages/bulk
 * Add multiple messages at once (mostly for migrations/sync)
 */
router.post('/:id/messages/bulk', async (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } });
    }

    const { id } = req.params;
    const { messages: messagesToAdd } = req.body;

    if (!Array.isArray(messagesToAdd) || messagesToAdd.length === 0) {
        return res.status(400).json({
            error: { code: 'VALIDATION_ERROR', message: 'Messages array is required' },
        });
    }

    const client = await getClient();

    try {
        await client.query('BEGIN');

        // Verify conversation ownership
        const convResult = await client.query(
            `SELECT id FROM conversations WHERE id = $1 AND user_id = $2`,
            [id, req.user.id]
        );

        if (convResult.rows.length === 0) {
            await client.query('ROLLBACK');
            return res.status(404).json({
                error: { code: 'NOT_FOUND', message: 'Conversation not found' },
            });
        }

        const insertedMessages: Message[] = [];
        let lastMessageId: string | null = null;

        for (const msg of messagesToAdd) {
            // If syncing from local DB, we might want to respect existing IDs?
            // For now, let's assume we generating new IDs on server
            const result = await client.query(
                `INSERT INTO messages (conversation_id, role, content, model, provider, reasoning_content, parent_id)
                 VALUES ($1, $2, $3, $4, $5, $6, $7)
                 RETURNING id, parent_id, role, content, model, provider, reasoning_content, created_at`,
                [id, msg.role, msg.content, msg.model || null, msg.provider || null, msg.reasoningContent || null, msg.parentId || null]
            );
            insertedMessages.push(result.rows[0]);
            lastMessageId = result.rows[0].id;
        }

        // Update conversation updated_at, set current_node to last inserted if not managed otherwise
        await client.query(
            `UPDATE conversations SET updated_at = NOW() WHERE id = $1`,
            [id]
        );

        if (lastMessageId) {
            // Only update current_node if it's null? Or always overwrite? 
            // Best to leave current_node logic to client/specific endpoint in bulk scenarios if unclear, 
            // but usually bulk add implies linear history or restore.
            // We'll skip forcing current_node update here to avoid breaking complex tree imports.
        }

        await client.query('COMMIT');

        res.status(201).json({ messages: insertedMessages });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('Error bulk adding messages:', error);
        res.status(500).json({
            error: { code: 'SERVER_ERROR', message: 'Failed to add messages' },
        });
    } finally {
        client.release();
    }
});

export default router;
