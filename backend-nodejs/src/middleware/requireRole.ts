/**
 * RBAC Middleware - Role-based access control
 * 
 * Usage:
 *   app.get('/admin', requireRole('admin', 'owner'), handler)
 *   app.get('/agent', requireRole('agent_user', 'admin', 'owner'), handler)
 */
import { Request, Response, NextFunction } from 'express';

// Role hierarchy (higher index = more permissions)
const ROLE_HIERARCHY = ['user', 'rag_user', 'agent_user', 'admin', 'owner'];

/**
 * Get role level in hierarchy
 */
function getRoleLevel(role: string): number {
    const level = ROLE_HIERARCHY.indexOf(role);
    return level >= 0 ? level : 0;
}

/**
 * Check if user role is at or above minimum required role
 */
export function hasMinRole(userRole: string, minRole: string): boolean {
    return getRoleLevel(userRole) >= getRoleLevel(minRole);
}

/**
 * Middleware to require specific roles
 * 
 * @param roles - List of allowed roles
 * @returns Express middleware
 */
export function requireRole(...roles: string[]) {
    return (req: Request, res: Response, next: NextFunction) => {
        const user = (req as any).user;

        if (!user) {
            return res.status(401).json({ error: 'Authentication required' });
        }

        const userRole = user.role || 'user';

        // Check if user has one of the required roles
        if (roles.includes(userRole)) {
            return next();
        }

        // Check if user's role is higher in hierarchy than any required role
        const minRequiredLevel = Math.min(...roles.map(r => getRoleLevel(r)));
        if (getRoleLevel(userRole) >= minRequiredLevel) {
            return next();
        }

        return res.status(403).json({
            error: 'Insufficient permissions',
            required: roles,
            current: userRole
        });
    };
}

/**
 * Middleware to require minimum role level
 * 
 * @param minRole - Minimum role level required
 * @returns Express middleware
 */
export function requireMinRole(minRole: string) {
    return (req: Request, res: Response, next: NextFunction) => {
        const user = (req as any).user;

        if (!user) {
            return res.status(401).json({ error: 'Authentication required' });
        }

        const userRole = user.role || 'user';

        if (hasMinRole(userRole, minRole)) {
            return next();
        }

        return res.status(403).json({
            error: 'Insufficient permissions',
            required: minRole,
            current: userRole
        });
    };
}

export default { requireRole, requireMinRole, hasMinRole, ROLE_HIERARCHY };
