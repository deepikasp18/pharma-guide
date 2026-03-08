"""
Encryption and data protection service for PharmaGuide
Implements AES-256 encryption for PII and PHI
"""
import logging
import hashlib
import secrets
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import re

logger = logging.getLogger(__name__)


@dataclass
class EncryptedData:
    """Encrypted data with metadata"""
    encrypted_value: str
    token: str  # Pseudonymized token for referencing
    encryption_timestamp: datetime
    key_version: str


class EncryptionService:
    """
    Service for encrypting PII and PHI data
    Uses AES-256 encryption via Fernet (symmetric encryption)
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.logger = logging.getLogger(__name__)
        
        # In production, master key would come from secure key management service
        if master_key is None:
            master_key = Fernet.generate_key()
        
        self.master_key = master_key
        self.fernet = Fernet(master_key)
        self.key_version = "v1"
        
        # PII/PHI field patterns
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
        }
        
        # PHI field names
        self.phi_fields = {
            'patient_name', 'date_of_birth', 'medical_record_number',
            'diagnosis', 'treatment', 'prescription', 'lab_results',
            'genetic_data', 'biometric_data', 'health_insurance_number'
        }
    
    def encrypt(self, data: str) -> EncryptedData:
        """
        Encrypt sensitive data using AES-256
        
        Args:
            data: Plain text data to encrypt
        
        Returns:
            Encrypted data with pseudonymized token
        """
        try:
            # Encrypt the data
            encrypted_bytes = self.fernet.encrypt(data.encode('utf-8'))
            encrypted_value = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            # Generate pseudonymized token
            token = self._generate_token(data)
            
            return EncryptedData(
                encrypted_value=encrypted_value,
                token=token,
                encryption_timestamp=datetime.utcnow(),
                key_version=self.key_version
            )
        
        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt(self, encrypted_data: EncryptedData) -> str:
        """
        Decrypt encrypted data
        
        Args:
            encrypted_data: Encrypted data object
        
        Returns:
            Decrypted plain text
        """
        try:
            # Decode and decrypt
            encrypted_bytes = base64.b64decode(encrypted_data.encrypted_value)
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            
            return decrypted_bytes.decode('utf-8')
        
        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            raise
    
    def _generate_token(self, data: str) -> str:
        """Generate pseudonymized token for data"""
        # Use SHA-256 hash as token
        hash_obj = hashlib.sha256(data.encode('utf-8'))
        token = hash_obj.hexdigest()[:16]  # Use first 16 chars
        return f"tok_{token}"
    
    def encrypt_dict(self, data: Dict[str, Any], sensitive_fields: Optional[list] = None) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary with potentially sensitive data
            sensitive_fields: List of field names to encrypt (if None, auto-detect)
        
        Returns:
            Dictionary with encrypted sensitive fields
        """
        try:
            encrypted_data = data.copy()
            
            # Auto-detect sensitive fields if not provided
            if sensitive_fields is None:
                sensitive_fields = self._detect_sensitive_fields(data)
            
            # Encrypt each sensitive field
            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    value = str(encrypted_data[field])
                    encrypted = self.encrypt(value)
                    
                    # Replace with encrypted version
                    encrypted_data[field] = {
                        'encrypted': True,
                        'value': encrypted.encrypted_value,
                        'token': encrypted.token,
                        'timestamp': encrypted.encryption_timestamp.isoformat()
                    }
            
            return encrypted_data
        
        except Exception as e:
            self.logger.error(f"Error encrypting dictionary: {e}")
            raise
    
    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt encrypted fields in a dictionary
        
        Args:
            data: Dictionary with encrypted fields
        
        Returns:
            Dictionary with decrypted fields
        """
        try:
            decrypted_data = data.copy()
            
            # Find and decrypt encrypted fields
            for field, value in data.items():
                if isinstance(value, dict) and value.get('encrypted'):
                    encrypted = EncryptedData(
                        encrypted_value=value['value'],
                        token=value['token'],
                        encryption_timestamp=datetime.fromisoformat(value['timestamp']),
                        key_version=self.key_version
                    )
                    decrypted_data[field] = self.decrypt(encrypted)
            
            return decrypted_data
        
        except Exception as e:
            self.logger.error(f"Error decrypting dictionary: {e}")
            raise
    
    def _detect_sensitive_fields(self, data: Dict[str, Any]) -> list:
        """Auto-detect sensitive fields in dictionary"""
        sensitive = []
        
        for field, value in data.items():
            # Check if field name indicates PHI
            if any(phi in field.lower() for phi in self.phi_fields):
                sensitive.append(field)
                continue
            
            # Check if value matches PII patterns
            if isinstance(value, str):
                for pattern_name, pattern in self.pii_patterns.items():
                    if pattern.search(value):
                        sensitive.append(field)
                        break
        
        return sensitive
    
    def sanitize_for_logging(self, data: Any) -> Any:
        """
        Sanitize data for logging by removing/masking PII/PHI
        
        Args:
            data: Data to sanitize
        
        Returns:
            Sanitized data safe for logging
        """
        try:
            if isinstance(data, dict):
                sanitized = {}
                for key, value in data.items():
                    # Check if field is sensitive
                    if any(phi in key.lower() for phi in self.phi_fields):
                        sanitized[key] = '[REDACTED]'
                    elif isinstance(value, str):
                        # Mask PII patterns
                        sanitized[key] = self._mask_pii(value)
                    elif isinstance(value, (dict, list)):
                        sanitized[key] = self.sanitize_for_logging(value)
                    else:
                        sanitized[key] = value
                return sanitized
            
            elif isinstance(data, list):
                return [self.sanitize_for_logging(item) for item in data]
            
            elif isinstance(data, str):
                return self._mask_pii(data)
            
            else:
                return data
        
        except Exception as e:
            self.logger.error(f"Error sanitizing data: {e}")
            return '[ERROR_SANITIZING]'
    
    def _mask_pii(self, text: str) -> str:
        """Mask PII patterns in text"""
        masked = text
        
        # Mask email addresses
        masked = self.pii_patterns['email'].sub('[EMAIL]', masked)
        
        # Mask SSN
        masked = self.pii_patterns['ssn'].sub('[SSN]', masked)
        
        # Mask phone numbers
        masked = self.pii_patterns['phone'].sub('[PHONE]', masked)
        
        # Mask credit cards
        masked = self.pii_patterns['credit_card'].sub('[CREDIT_CARD]', masked)
        
        return masked
    
    def generate_pseudonym(self, identifier: str) -> str:
        """
        Generate consistent pseudonym for an identifier
        
        Args:
            identifier: Original identifier
        
        Returns:
            Pseudonymized identifier
        """
        # Use HMAC for consistent pseudonymization
        hash_obj = hashlib.sha256(
            (identifier + self.key_version).encode('utf-8')
        )
        return f"pseudo_{hash_obj.hexdigest()[:16]}"
    
    def tokenize(self, data: str) -> str:
        """
        Tokenize sensitive data (one-way, cannot be reversed)
        
        Args:
            data: Data to tokenize
        
        Returns:
            Token representing the data
        """
        return self._generate_token(data)


# Factory function
def create_encryption_service(master_key: Optional[bytes] = None) -> EncryptionService:
    """Create encryption service"""
    return EncryptionService(master_key)
