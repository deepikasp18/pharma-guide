"""
Access control and audit trail service for PharmaGuide
Implements role-based access controls and comprehensive audit logging
"""
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    CLINICIAN = "clinician"
    PHARMACIST = "pharmacist"
    RESEARCHER = "researcher"
    PATIENT = "patient"
    READONLY = "readonly"


class Permission(str, Enum):
    """Permissions"""
    READ_PII = "read_pii"
    READ_PHI = "read_phi"
    WRITE_PII = "write_pii"
    WRITE_PHI = "write_phi"
    READ_DRUG_INFO = "read_drug_info"
    WRITE_DRUG_INFO = "write_drug_info"
    READ_INTERACTIONS = "read_interactions"
    QUERY_KNOWLEDGE_GRAPH = "query_knowledge_graph"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"


class AuditAction(str, Enum):
    """Audit actions"""
    LOGIN = "login"
    LOGOUT = "logout"
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    EXPORT = "export"
    ACCESS_DENIED = "access_denied"


@dataclass
class User:
    """User with roles and permissions"""
    user_id: str
    username: str
    roles: List[Role]
    permissions: Set[Permission]
    active: bool
    created_at: datetime
    last_login: Optional[datetime]


@dataclass
class AuditLogEntry:
    """Audit log entry"""
    log_id: str
    timestamp: datetime
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    success: bool
    ip_address: Optional[str]
    details: Dict[str, Any]
    sensitive_data_accessed: bool


class AccessControlService:
    """
    Service for managing access control and audit trails
    Implements RBAC (Role-Based Access Control)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Role to permissions mapping
        self.role_permissions = {
            Role.ADMIN: {
                Permission.READ_PII, Permission.READ_PHI,
                Permission.WRITE_PII, Permission.WRITE_PHI,
                Permission.READ_DRUG_INFO, Permission.WRITE_DRUG_INFO,
                Permission.READ_INTERACTIONS, Permission.QUERY_KNOWLEDGE_GRAPH,
                Permission.MANAGE_USERS, Permission.VIEW_AUDIT_LOGS
            },
            Role.CLINICIAN: {
                Permission.READ_PII, Permission.READ_PHI,
                Permission.WRITE_PHI, Permission.READ_DRUG_INFO,
                Permission.READ_INTERACTIONS, Permission.QUERY_KNOWLEDGE_GRAPH
            },
            Role.PHARMACIST: {
                Permission.READ_PII, Permission.READ_PHI,
                Permission.READ_DRUG_INFO, Permission.READ_INTERACTIONS,
                Permission.QUERY_KNOWLEDGE_GRAPH
            },
            Role.RESEARCHER: {
                Permission.READ_DRUG_INFO, Permission.READ_INTERACTIONS,
                Permission.QUERY_KNOWLEDGE_GRAPH
            },
            Role.PATIENT: {
                Permission.READ_DRUG_INFO, Permission.READ_INTERACTIONS
            },
            Role.READONLY: {
                Permission.READ_DRUG_INFO
            }
        }
        
        # In-memory user store (in production, would use database)
        self.users: Dict[str, User] = {}
        
        # In-memory audit log (in production, would use persistent storage)
        self.audit_logs: List[AuditLogEntry] = []
    
    def create_user(
        self,
        user_id: str,
        username: str,
        roles: List[Role]
    ) -> User:
        """
        Create a new user with specified roles
        
        Args:
            user_id: Unique user identifier
            username: Username
            roles: List of roles to assign
        
        Returns:
            Created user
        """
        try:
            # Calculate permissions from roles
            permissions = set()
            for role in roles:
                permissions.update(self.role_permissions.get(role, set()))
            
            user = User(
                user_id=user_id,
                username=username,
                roles=roles,
                permissions=permissions,
                active=True,
                created_at=datetime.utcnow(),
                last_login=None
            )
            
            self.users[user_id] = user
            self.logger.info(f"Created user {username} with roles {roles}")
            
            return user
        
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            raise
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user_id: User identifier
            permission: Permission to check
        
        Returns:
            True if user has permission, False otherwise
        """
        try:
            user = self.users.get(user_id)
            
            if not user:
                self.logger.warning(f"User {user_id} not found")
                return False
            
            if not user.active:
                self.logger.warning(f"User {user_id} is inactive")
                return False
            
            has_permission = permission in user.permissions
            
            if not has_permission:
                self.logger.warning(
                    f"User {user_id} denied permission {permission}"
                )
            
            return has_permission
        
        except Exception as e:
            self.logger.error(f"Error checking permission: {e}")
            return False
    
    def authorize_action(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        required_permission: Permission
    ) -> bool:
        """
        Authorize user action and log to audit trail
        
        Args:
            user_id: User identifier
            action: Action being performed
            resource_type: Type of resource being accessed
            resource_id: Resource identifier
            required_permission: Permission required for action
        
        Returns:
            True if authorized, False otherwise
        """
        try:
            # Check permission
            authorized = self.check_permission(user_id, required_permission)
            
            # Log to audit trail
            self.log_audit_event(
                user_id=user_id,
                action=action if authorized else AuditAction.ACCESS_DENIED,
                resource_type=resource_type,
                resource_id=resource_id,
                success=authorized,
                details={
                    'required_permission': required_permission.value,
                    'authorized': authorized
                },
                sensitive_data_accessed=self._is_sensitive_resource(resource_type)
            )
            
            return authorized
        
        except Exception as e:
            self.logger.error(f"Error authorizing action: {e}")
            return False
    
    def log_audit_event(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        sensitive_data_accessed: bool = False
    ) -> AuditLogEntry:
        """
        Log an audit event
        
        Args:
            user_id: User identifier
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource identifier
            success: Whether action succeeded
            details: Additional details (will be sanitized)
            ip_address: IP address of request
            sensitive_data_accessed: Whether sensitive data was accessed
        
        Returns:
            Audit log entry
        """
        try:
            # Sanitize details to remove sensitive data
            sanitized_details = self._sanitize_audit_details(details or {})
            
            log_entry = AuditLogEntry(
                log_id=f"audit_{len(self.audit_logs) + 1}",
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                ip_address=ip_address,
                details=sanitized_details,
                sensitive_data_accessed=sensitive_data_accessed
            )
            
            self.audit_logs.append(log_entry)
            
            # Log to system logger (without sensitive details)
            self.logger.info(
                f"Audit: user={user_id} action={action.value} "
                f"resource={resource_type}/{resource_id} success={success}"
            )
            
            return log_entry
        
        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")
            raise
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit logs with filters
        
        Args:
            user_id: Filter by user
            action: Filter by action
            resource_type: Filter by resource type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of logs to return
        
        Returns:
            List of audit log entries
        """
        try:
            filtered_logs = self.audit_logs
            
            # Apply filters
            if user_id:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.user_id == user_id
                ]
            
            if action:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.action == action
                ]
            
            if resource_type:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.resource_type == resource_type
                ]
            
            if start_time:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.timestamp >= start_time
                ]
            
            if end_time:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.timestamp <= end_time
                ]
            
            # Sort by timestamp (most recent first)
            filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            return filtered_logs[:limit]
        
        except Exception as e:
            self.logger.error(f"Error retrieving audit logs: {e}")
            return []
    
    def _is_sensitive_resource(self, resource_type: str) -> bool:
        """Check if resource type contains sensitive data"""
        sensitive_types = {
            'patient', 'pii', 'phi', 'medical_record',
            'prescription', 'diagnosis', 'genetic_data'
        }
        return any(
            sensitive in resource_type.lower()
            for sensitive in sensitive_types
        )
    
    def _sanitize_audit_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize audit details to remove sensitive data"""
        sanitized = {}
        
        sensitive_keys = {
            'password', 'token', 'api_key', 'secret',
            'ssn', 'credit_card', 'patient_name', 'dob'
        }
        
        for key, value in details.items():
            # Check if key indicates sensitive data
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_audit_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_audit_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def revoke_user_access(self, user_id: str) -> bool:
        """
        Revoke user access (deactivate user)
        
        Args:
            user_id: User identifier
        
        Returns:
            True if successful
        """
        try:
            user = self.users.get(user_id)
            
            if not user:
                self.logger.warning(f"User {user_id} not found")
                return False
            
            user.active = False
            self.logger.info(f"Revoked access for user {user_id}")
            
            # Log audit event
            self.log_audit_event(
                user_id='system',
                action=AuditAction.UPDATE,
                resource_type='user',
                resource_id=user_id,
                success=True,
                details={'action': 'revoke_access'}
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error revoking user access: {e}")
            return False
    
    def add_role_to_user(self, user_id: str, role: Role) -> bool:
        """
        Add role to user
        
        Args:
            user_id: User identifier
            role: Role to add
        
        Returns:
            True if successful
        """
        try:
            user = self.users.get(user_id)
            
            if not user:
                self.logger.warning(f"User {user_id} not found")
                return False
            
            if role not in user.roles:
                user.roles.append(role)
                
                # Update permissions
                user.permissions.update(self.role_permissions.get(role, set()))
                
                self.logger.info(f"Added role {role} to user {user_id}")
                
                # Log audit event
                self.log_audit_event(
                    user_id='system',
                    action=AuditAction.UPDATE,
                    resource_type='user',
                    resource_id=user_id,
                    success=True,
                    details={'action': 'add_role', 'role': role.value}
                )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding role to user: {e}")
            return False
    
    def remove_role_from_user(self, user_id: str, role: Role) -> bool:
        """
        Remove role from user
        
        Args:
            user_id: User identifier
            role: Role to remove
        
        Returns:
            True if successful
        """
        try:
            user = self.users.get(user_id)
            
            if not user:
                self.logger.warning(f"User {user_id} not found")
                return False
            
            if role in user.roles:
                user.roles.remove(role)
                
                # Recalculate permissions
                user.permissions = set()
                for r in user.roles:
                    user.permissions.update(self.role_permissions.get(r, set()))
                
                self.logger.info(f"Removed role {role} from user {user_id}")
                
                # Log audit event
                self.log_audit_event(
                    user_id='system',
                    action=AuditAction.UPDATE,
                    resource_type='user',
                    resource_id=user_id,
                    success=True,
                    details={'action': 'remove_role', 'role': role.value}
                )
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error removing role from user: {e}")
            return False


# Factory function
def create_access_control_service() -> AccessControlService:
    """Create access control service"""
    return AccessControlService()
