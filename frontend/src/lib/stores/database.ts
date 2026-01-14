import Dexie, { type EntityTable } from 'dexie';
import { filterByLeafNodeId, findDescendantMessages } from '$lib/utils/branching';
import { v4 as uuid } from 'uuid';
import { conversationsApi, type ApiConversation, type ApiMessage } from '$lib/services/conversationsApi';
import { getAccessToken } from '$lib/services/api';

class LlamacppDatabase extends Dexie {
	conversations!: EntityTable<DatabaseConversation, string>;
	messages!: EntityTable<DatabaseMessage, string>;

	constructor() {
		super('LlamacppWebui');

		this.version(1).stores({
			conversations: 'id, lastModified, currNode, name',
			messages: 'id, convId, type, role, timestamp, parent, children'
		});
	}
}

const db = new LlamacppDatabase();

/**
 * Check if user is authenticated and should use API storage
 */
function useApiStorage(): boolean {
	return !!getAccessToken();
}

/**
 * Convert API conversation to database format
 */
function apiConvToDb(apiConv: ApiConversation): DatabaseConversation {
	return {
		id: apiConv.id,
		name: apiConv.name || 'Untitled',
		lastModified: new Date(apiConv.updated_at).getTime(),
		currNode: apiConv.current_node || ''
	};
}

/**
 * Convert API message to database format
 */
function apiMsgToDb(apiMsg: ApiMessage, convId: string): DatabaseMessage {
	return {
		id: apiMsg.id,
		convId,
		type: 'text',
		timestamp: new Date(apiMsg.created_at).getTime(),
		role: apiMsg.role as ChatRole,
		content: apiMsg.content,
		parent: apiMsg.parent_id || '',
		thinking: apiMsg.reasoning_content || '',
		toolCalls: '',
		children: [], // Will be computed from parent relationships
		model: apiMsg.model || undefined
	};
}

/**
 * Build children arrays from parent relationships
 */
function buildChildrenArrays(messages: DatabaseMessage[]): DatabaseMessage[] {
	const messageMap = new Map<string, DatabaseMessage>();
	messages.forEach(msg => {
		msg.children = [];
		messageMap.set(msg.id, msg);
	});

	messages.forEach(msg => {
		if (msg.parent && messageMap.has(msg.parent)) {
			const parent = messageMap.get(msg.parent)!;
			parent.children.push(msg.id);
		}
	});

	return messages;
}

/**
 * DatabaseStore - Persistent data layer for conversation and message management
 *
 * This service provides a comprehensive data access layer that uses:
 * - Backend API (PostgreSQL) when user is authenticated
 * - IndexedDB (Dexie) when user is not authenticated (local storage)
 */
export class DatabaseStore {
	/**
	 * Adds a new message to the database.
	 */
	static async addMessage(message: Omit<DatabaseMessage, 'id'>): Promise<DatabaseMessage> {
		const newMessage: DatabaseMessage = {
			...message,
			id: uuid()
		};

		if (useApiStorage()) {
			try {
				const apiMsg = await conversationsApi.addMessage(message.convId, {
					role: message.role,
					content: message.content,
					parent_id: message.parent || null,
					model: message.model,
					reasoning_content: message.thinking
				});
				return apiMsgToDb(apiMsg, message.convId);
			} catch (error) {
				console.error('API addMessage failed, falling back to IndexedDB:', error);
			}
		}

		await db.messages.add(newMessage);
		return newMessage;
	}

	/**
	 * Creates a new conversation.
	 */
	static async createConversation(name: string): Promise<DatabaseConversation> {
		if (useApiStorage()) {
			try {
				const apiConv = await conversationsApi.create(name);
				return apiConvToDb(apiConv);
			} catch (error) {
				console.error('API createConversation failed, falling back to IndexedDB:', error);
			}
		}

		const conversation: DatabaseConversation = {
			id: uuid(),
			name,
			lastModified: Date.now(),
			currNode: ''
		};

		await db.conversations.add(conversation);
		return conversation;
	}

	/**
	 * Creates a new message branch by adding a message and updating parent/child relationships.
	 */
	static async createMessageBranch(
		message: Omit<DatabaseMessage, 'id'>,
		parentId: string | null
	): Promise<DatabaseMessage> {
		if (useApiStorage()) {
			const apiMsg = await conversationsApi.addMessage(message.convId, {
				role: message.role,
				content: message.content,
				parent_id: parentId,
				model: message.model,
				reasoning_content: message.thinking
			});

			// Also update current_node
			await conversationsApi.update(message.convId, { current_node: apiMsg.id });

			return apiMsgToDb(apiMsg, message.convId);
		}

		return await db.transaction('rw', [db.conversations, db.messages], async () => {
			if (parentId !== null) {
				const parentMessage = await db.messages.get(parentId);
				if (!parentMessage) {
					throw new Error(`Parent message ${parentId} not found`);
				}
			}

			const newMessage: DatabaseMessage = {
				...message,
				id: uuid(),
				parent: parentId,
				toolCalls: message.toolCalls ?? '',
				children: []
			};

			await db.messages.add(newMessage);

			if (parentId !== null) {
				const parentMessage = await db.messages.get(parentId);
				if (parentMessage) {
					await db.messages.update(parentId, {
						children: [...parentMessage.children, newMessage.id]
					});
				}
			}

			await this.updateConversation(message.convId, {
				currNode: newMessage.id
			});

			return newMessage;
		});
	}

	/**
	 * Creates a root message for a new conversation.
	 */
	static async createRootMessage(convId: string): Promise<string> {
		const rootMessage: DatabaseMessage = {
			id: uuid(),
			convId,
			type: 'root',
			timestamp: Date.now(),
			role: 'system',
			content: '',
			parent: null,
			thinking: '',
			toolCalls: '',
			children: []
		};

		if (useApiStorage()) {
			try {
				const apiMsg = await conversationsApi.addMessage(convId, {
					role: 'system',
					content: '',
					parent_id: null
				});
				return apiMsg.id;
			} catch (error) {
				console.error('API createRootMessage failed, falling back to IndexedDB:', error);
			}
		}

		await db.messages.add(rootMessage);
		return rootMessage.id;
	}

	/**
	 * Deletes a conversation and all its messages.
	 */
	static async deleteConversation(id: string): Promise<void> {
		if (useApiStorage()) {
			try {
				await conversationsApi.delete(id);
				return;
			} catch (error) {
				console.error('API deleteConversation failed, falling back to IndexedDB:', error);
			}
		}

		await db.transaction('rw', [db.conversations, db.messages], async () => {
			await db.conversations.delete(id);
			await db.messages.where('convId').equals(id).delete();
		});
	}

	/**
	 * Deletes a message and removes it from its parent's children array.
	 */
	static async deleteMessage(messageId: string): Promise<void> {
		// For API, we don't have a delete message endpoint yet
		// Fall through to IndexedDB
		await db.transaction('rw', db.messages, async () => {
			const message = await db.messages.get(messageId);
			if (!message) return;

			if (message.parent) {
				const parent = await db.messages.get(message.parent);
				if (parent) {
					parent.children = parent.children.filter((childId: string) => childId !== messageId);
					await db.messages.put(parent);
				}
			}

			await db.messages.delete(messageId);
		});
	}

	/**
	 * Deletes a message and all its descendant messages (cascading deletion).
	 */
	static async deleteMessageCascading(
		conversationId: string,
		messageId: string
	): Promise<string[]> {
		return await db.transaction('rw', db.messages, async () => {
			const allMessages = await db.messages.where('convId').equals(conversationId).toArray();
			const descendants = findDescendantMessages(allMessages, messageId);
			const allToDelete = [messageId, ...descendants];

			const message = await db.messages.get(messageId);
			if (message && message.parent) {
				const parent = await db.messages.get(message.parent);
				if (parent) {
					parent.children = parent.children.filter((childId: string) => childId !== messageId);
					await db.messages.put(parent);
				}
			}

			await db.messages.bulkDelete(allToDelete);
			return allToDelete;
		});
	}

	/**
	 * Gets all conversations, sorted by last modified time (newest first).
	 */
	static async getAllConversations(): Promise<DatabaseConversation[]> {
		if (useApiStorage()) {
			try {
				const apiConvs = await conversationsApi.list();
				return apiConvs.map(apiConvToDb);
			} catch (error) {
				console.error('API getAllConversations failed, falling back to IndexedDB:', error);
			}
		}

		return await db.conversations.orderBy('lastModified').reverse().toArray();
	}

	/**
	 * Gets a conversation by ID.
	 */
	static async getConversation(id: string): Promise<DatabaseConversation | undefined> {
		if (useApiStorage()) {
			try {
				const { conversation } = await conversationsApi.get(id);
				return apiConvToDb(conversation);
			} catch (error) {
				console.error('API getConversation failed, falling back to IndexedDB:', error);
			}
		}

		return await db.conversations.get(id);
	}

	/**
	 * Gets all leaf nodes (messages with no children) in a conversation.
	 */
	static async getConversationLeafNodes(convId: string): Promise<string[]> {
		const allMessages = await this.getConversationMessages(convId);
		return allMessages.filter((msg) => msg.children.length === 0).map((msg) => msg.id);
	}

	/**
	 * Gets all messages in a conversation, sorted by timestamp (oldest first).
	 */
	static async getConversationMessages(convId: string): Promise<DatabaseMessage[]> {
		if (useApiStorage()) {
			try {
				const { messages } = await conversationsApi.get(convId);
				const dbMessages = messages.map(msg => apiMsgToDb(msg, convId));
				return buildChildrenArrays(dbMessages).sort((a, b) => a.timestamp - b.timestamp);
			} catch (error) {
				console.error('API getConversationMessages failed, falling back to IndexedDB:', error);
			}
		}

		return await db.messages.where('convId').equals(convId).sortBy('timestamp');
	}

	/**
	 * Gets the conversation path from root to the current leaf node.
	 */
	static async getConversationPath(convId: string): Promise<DatabaseMessage[]> {
		const conversation = await this.getConversation(convId);

		if (!conversation) {
			return [];
		}

		const allMessages = await this.getConversationMessages(convId);

		if (allMessages.length === 0) {
			return [];
		}

		const leafNodeId =
			conversation.currNode ||
			allMessages.reduce((latest, msg) => (msg.timestamp > latest.timestamp ? msg : latest)).id;

		return filterByLeafNodeId(allMessages, leafNodeId, false) as DatabaseMessage[];
	}

	/**
	 * Updates a conversation.
	 */
	static async updateConversation(
		id: string,
		updates: Partial<Omit<DatabaseConversation, 'id'>>
	): Promise<void> {
		if (useApiStorage()) {
			try {
				await conversationsApi.update(id, {
					name: updates.name,
					current_node: updates.currNode || undefined
				});
				return;
			} catch (error) {
				console.error('API updateConversation failed, falling back to IndexedDB:', error);
			}
		}

		await db.conversations.update(id, {
			...updates,
			lastModified: Date.now()
		});
	}

	/**
	 * Updates the conversation's current node (active branch).
	 */
	static async updateCurrentNode(convId: string, nodeId: string): Promise<void> {
		await this.updateConversation(convId, {
			currNode: nodeId
		});
	}

	/**
	 * Updates a message.
	 */
	static async updateMessage(
		id: string,
		updates: Partial<Omit<DatabaseMessage, 'id'>>
	): Promise<void> {
		// For now, only update in IndexedDB
		// API message updates not yet implemented
		await db.messages.update(id, updates);
	}

	/**
	 * Imports multiple conversations and their messages.
	 */
	static async importConversations(
		data: { conv: DatabaseConversation; messages: DatabaseMessage[] }[]
	): Promise<{ imported: number; skipped: number }> {
		let importedCount = 0;
		let skippedCount = 0;

		return await db.transaction('rw', [db.conversations, db.messages], async () => {
			for (const item of data) {
				const { conv, messages } = item;

				const existing = await db.conversations.get(conv.id);
				if (existing) {
					console.warn(`Conversation "${conv.name}" already exists, skipping...`);
					skippedCount++;
					continue;
				}

				await db.conversations.add(conv);
				for (const msg of messages) {
					await db.messages.put(msg);
				}

				importedCount++;
			}

			return { imported: importedCount, skipped: skippedCount };
		});
	}
}
