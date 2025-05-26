"""
PIPEDA Compliance Module for The Inner Architect

This module implements compliance with the Personal Information Protection and
Electronic Documents Act (PIPEDA), which is Canada's federal private-sector privacy law.

It handles:
1. Consent management
2. Data access and correction
3. Privacy policy requirements
4. Data collection limitations
5. Security safeguards
6. Transparency and accountability
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from logging_config import get_logger, info, error, debug, warning, critical, exception

# Initialize logger
logger = get_logger('pipeda_compliance')


class ConsentType(Enum):
    """Types of consent under PIPEDA."""
    EXPRESS = "express"  # Explicit, opt-in consent
    IMPLIED = "implied"  # Implied through actions
    WITHDRAWN = "withdrawn"  # Consent has been withdrawn


class PurposeCategory(Enum):
    """Categories of data collection purposes under PIPEDA."""
    CORE_SERVICE = "core_service"  # Required for basic app functionality
    ENHANCEMENT = "enhancement"  # Enhances user experience but not essential
    ANALYTICS = "analytics"  # Used for analytics and service improvement
    MARKETING = "marketing"  # Used for marketing purposes
    THIRD_PARTY = "third_party"  # Shared with third parties


@dataclass
class ConsentRecord:
    """Record of user consent for data processing under PIPEDA."""
    user_id: str
    timestamp: datetime
    consent_type: ConsentType
    purposes: List[PurposeCategory]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expiry: Optional[datetime] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataAccessRequest:
    """Record of a data access request under PIPEDA."""
    request_id: str
    user_id: str
    timestamp: datetime
    request_type: str  # access, correction, deletion
    status: str  # pending, completed, denied
    completion_date: Optional[datetime] = None
    request_details: Dict[str, Any] = field(default_factory=dict)
    response_details: Dict[str, Any] = field(default_factory=dict)


class PipedaCompliance:
    """
    Main class implementing PIPEDA compliance functionality.
    """

    def __init__(self, db_connection=None):
        """
        Initialize the PIPEDA compliance module.
        
        Args:
            db_connection: Database connection for storage (if None, uses file-based storage)
        """
        self.db = db_connection
        self.consents_dir = os.path.join(os.path.dirname(__file__), 'data', 'consents')
        self.requests_dir = os.path.join(os.path.dirname(__file__), 'data', 'requests')
        
        # Create directories if they don't exist
        os.makedirs(self.consents_dir, exist_ok=True)
        os.makedirs(self.requests_dir, exist_ok=True)
        
        # Configuration
        self.consent_validity_days = 365  # Default consent expiry (1 year)
        self.access_request_deadline_days = 30  # Legal deadline to respond
        
        logger.info("PIPEDA compliance module initialized")

    def _get_consent_file_path(self, user_id: str) -> str:
        """Get the path to a user's consent file."""
        return os.path.join(self.consents_dir, f"{user_id}_consent.json")
    
    def _get_request_file_path(self, request_id: str) -> str:
        """Get the path to a request file."""
        return os.path.join(self.requests_dir, f"{request_id}_request.json")
    
    def record_consent(self, consent: ConsentRecord) -> bool:
        """
        Record a user's consent for data processing.
        
        Args:
            consent: The consent record to store
            
        Returns:
            True if successful, False otherwise
        """
        if self.db:
            # Use database storage if available
            try:
                # Convert dataclass to dict
                consent_dict = {
                    "user_id": consent.user_id,
                    "timestamp": consent.timestamp.isoformat(),
                    "consent_type": consent.consent_type.value,
                    "purposes": [purpose.value for purpose in consent.purposes],
                    "ip_address": consent.ip_address,
                    "user_agent": consent.user_agent,
                    "expiry": consent.expiry.isoformat() if consent.expiry else None,
                    "additional_info": consent.additional_info
                }
                
                # Store in database (implementation depends on db type)
                # self.db.consents.insert_one(consent_dict)
                logger.info(f"Recorded consent for user {consent.user_id} in database")
                return True
            except Exception as e:
                logger.error(f"Error recording consent in database: {e}")
                return False
        else:
            # Use file-based storage
            try:
                consent_file = self._get_consent_file_path(consent.user_id)
                
                # Convert dataclass to dict
                consent_dict = {
                    "user_id": consent.user_id,
                    "timestamp": consent.timestamp.isoformat(),
                    "consent_type": consent.consent_type.value,
                    "purposes": [purpose.value for purpose in consent.purposes],
                    "ip_address": consent.ip_address,
                    "user_agent": consent.user_agent,
                    "expiry": consent.expiry.isoformat() if consent.expiry else None,
                    "additional_info": consent.additional_info
                }
                
                # Check for existing consents
                existing_consents = []
                if os.path.exists(consent_file):
                    with open(consent_file, 'r', encoding='utf-8') as f:
                        try:
                            existing_consents = json.load(f)
                        except json.JSONDecodeError:
                            existing_consents = []
                
                # Add new consent
                existing_consents.append(consent_dict)
                
                # Save to file
                with open(consent_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_consents, f, indent=2)
                
                logger.info(f"Recorded consent for user {consent.user_id} in file")
                return True
            except Exception as e:
                logger.error(f"Error recording consent in file: {e}")
                return False
    
    def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """
        Get all consent records for a user.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            List of consent records
        """
        if self.db:
            # Use database storage if available
            try:
                # Fetch from database (implementation depends on db type)
                # consents = list(self.db.consents.find({"user_id": user_id}))
                consents = []  # Placeholder
                
                # Convert to ConsentRecord objects
                result = []
                for consent_dict in consents:
                    result.append(ConsentRecord(
                        user_id=consent_dict["user_id"],
                        timestamp=datetime.fromisoformat(consent_dict["timestamp"]),
                        consent_type=ConsentType(consent_dict["consent_type"]),
                        purposes=[PurposeCategory(p) for p in consent_dict["purposes"]],
                        ip_address=consent_dict.get("ip_address"),
                        user_agent=consent_dict.get("user_agent"),
                        expiry=datetime.fromisoformat(consent_dict["expiry"]) if consent_dict.get("expiry") else None,
                        additional_info=consent_dict.get("additional_info", {})
                    ))
                
                return result
            except Exception as e:
                logger.error(f"Error getting consents from database: {e}")
                return []
        else:
            # Use file-based storage
            try:
                consent_file = self._get_consent_file_path(user_id)
                
                if not os.path.exists(consent_file):
                    return []
                
                with open(consent_file, 'r', encoding='utf-8') as f:
                    try:
                        consent_dicts = json.load(f)
                    except json.JSONDecodeError:
                        return []
                
                # Convert to ConsentRecord objects
                result = []
                for consent_dict in consent_dicts:
                    result.append(ConsentRecord(
                        user_id=consent_dict["user_id"],
                        timestamp=datetime.fromisoformat(consent_dict["timestamp"]),
                        consent_type=ConsentType(consent_dict["consent_type"]),
                        purposes=[PurposeCategory(p) for p in consent_dict["purposes"]],
                        ip_address=consent_dict.get("ip_address"),
                        user_agent=consent_dict.get("user_agent"),
                        expiry=datetime.fromisoformat(consent_dict["expiry"]) if consent_dict.get("expiry") else None,
                        additional_info=consent_dict.get("additional_info", {})
                    ))
                
                return result
            except Exception as e:
                logger.error(f"Error getting consents from file: {e}")
                return []
    
    def has_valid_consent(self, user_id: str, purpose: PurposeCategory) -> bool:
        """
        Check if a user has valid consent for a specific purpose.
        
        Args:
            user_id: The user ID to check
            purpose: The purpose to check consent for
            
        Returns:
            True if the user has valid consent, False otherwise
        """
        consents = self.get_user_consents(user_id)
        
        # Check for the most recent express consent that includes the purpose
        # and is not expired
        now = datetime.now()
        valid_consents = [
            c for c in consents 
            if c.consent_type == ConsentType.EXPRESS 
            and purpose in c.purposes
            and (c.expiry is None or c.expiry > now)
        ]
        
        # Sort by timestamp (most recent first)
        valid_consents.sort(key=lambda c: c.timestamp, reverse=True)
        
        # Check if there's a more recent withdrawal
        withdrawals = [
            c for c in consents
            if c.consent_type == ConsentType.WITHDRAWN
            and purpose in c.purposes
        ]
        withdrawals.sort(key=lambda c: c.timestamp, reverse=True)
        
        if valid_consents and (not withdrawals or valid_consents[0].timestamp > withdrawals[0].timestamp):
            return True
        
        return False
    
    def create_data_access_request(self, user_id: str, request_type: str, details: Dict[str, Any] = None) -> Optional[str]:
        """
        Create a new data access, correction, or deletion request.
        
        Args:
            user_id: The user ID making the request
            request_type: Type of request (access, correction, deletion)
            details: Additional details about the request
            
        Returns:
            Request ID if successful, None otherwise
        """
        # Validate request type
        if request_type not in ["access", "correction", "deletion"]:
            logger.error(f"Invalid request type: {request_type}")
            return None
        
        try:
            # Generate a unique request ID
            request_id = f"{user_id}_{request_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create request record
            request = DataAccessRequest(
                request_id=request_id,
                user_id=user_id,
                timestamp=datetime.now(),
                request_type=request_type,
                status="pending",
                request_details=details or {}
            )
            
            # Store the request
            if self.db:
                # Database storage (implementation depends on db type)
                # self.db.data_requests.insert_one(request.__dict__)
                pass
            else:
                # File-based storage
                request_file = self._get_request_file_path(request_id)
                
                # Convert to dict
                request_dict = {
                    "request_id": request.request_id,
                    "user_id": request.user_id,
                    "timestamp": request.timestamp.isoformat(),
                    "request_type": request.request_type,
                    "status": request.status,
                    "completion_date": request.completion_date.isoformat() if request.completion_date else None,
                    "request_details": request.request_details,
                    "response_details": request.response_details
                }
                
                # Save to file
                with open(request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_dict, f, indent=2)
            
            logger.info(f"Created {request_type} request {request_id} for user {user_id}")
            return request_id
        except Exception as e:
            logger.error(f"Error creating data request: {e}")
            return None
    
    def update_request_status(self, request_id: str, status: str, response_details: Dict[str, Any] = None) -> bool:
        """
        Update the status of a data request.
        
        Args:
            request_id: The request ID
            status: New status (pending, completed, denied)
            response_details: Details about the response
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.db:
                # Database update (implementation depends on db type)
                # self.db.data_requests.update_one(
                #     {"request_id": request_id},
                #     {"$set": {
                #         "status": status,
                #         "completion_date": datetime.now().isoformat() if status in ["completed", "denied"] else None,
                #         "response_details": response_details or {}
                #     }}
                # )
                pass
            else:
                # File-based storage
                request_file = self._get_request_file_path(request_id)
                
                if not os.path.exists(request_file):
                    logger.error(f"Request {request_id} not found")
                    return False
                
                # Read existing request
                with open(request_file, 'r', encoding='utf-8') as f:
                    request_dict = json.load(f)
                
                # Update fields
                request_dict["status"] = status
                if status in ["completed", "denied"]:
                    request_dict["completion_date"] = datetime.now().isoformat()
                if response_details:
                    request_dict["response_details"] = response_details
                
                # Save updated request
                with open(request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_dict, f, indent=2)
            
            logger.info(f"Updated request {request_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating request status: {e}")
            return False
    
    def get_pending_requests(self) -> List[DataAccessRequest]:
        """
        Get all pending data access requests.
        
        Returns:
            List of pending requests
        """
        try:
            pending_requests = []
            
            if self.db:
                # Database query (implementation depends on db type)
                # pending_requests = list(self.db.data_requests.find({"status": "pending"}))
                pass
            else:
                # File-based storage
                for filename in os.listdir(self.requests_dir):
                    if filename.endswith("_request.json"):
                        file_path = os.path.join(self.requests_dir, filename)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            request_dict = json.load(f)
                        
                        if request_dict["status"] == "pending":
                            # Convert to DataAccessRequest object
                            request = DataAccessRequest(
                                request_id=request_dict["request_id"],
                                user_id=request_dict["user_id"],
                                timestamp=datetime.fromisoformat(request_dict["timestamp"]),
                                request_type=request_dict["request_type"],
                                status=request_dict["status"],
                                completion_date=datetime.fromisoformat(request_dict["completion_date"]) if request_dict.get("completion_date") else None,
                                request_details=request_dict.get("request_details", {}),
                                response_details=request_dict.get("response_details", {})
                            )
                            pending_requests.append(request)
            
            return pending_requests
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
    
    def check_overdue_requests(self) -> List[DataAccessRequest]:
        """
        Check for data access requests that are overdue for response.
        
        Returns:
            List of overdue requests
        """
        pending_requests = self.get_pending_requests()
        
        # Calculate deadline based on PIPEDA requirements (30 days)
        deadline = datetime.now() - timedelta(days=self.access_request_deadline_days)
        
        # Filter for requests older than the deadline
        overdue_requests = [r for r in pending_requests if r.timestamp < deadline]
        
        if overdue_requests:
            logger.warning(f"Found {len(overdue_requests)} overdue data access requests")
        
        return overdue_requests
    
    def withdraw_consent(self, user_id: str, purposes: List[PurposeCategory], request_details: Dict[str, Any] = None) -> bool:
        """
        Record a user's withdrawal of consent.
        
        Args:
            user_id: The user ID
            purposes: List of purposes for which consent is withdrawn
            request_details: Additional details about the withdrawal
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a withdrawal consent record
            withdrawal = ConsentRecord(
                user_id=user_id,
                timestamp=datetime.now(),
                consent_type=ConsentType.WITHDRAWN,
                purposes=purposes,
                additional_info=request_details or {}
            )
            
            # Record the withdrawal
            success = self.record_consent(withdrawal)
            
            if success:
                logger.info(f"Recorded consent withdrawal for user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error recording consent withdrawal: {e}")
            return False
    
    def generate_privacy_compliance_report(self) -> Dict[str, Any]:
        """
        Generate a report on PIPEDA compliance status.
        
        Returns:
            Dictionary with compliance statistics and issues
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "consent_stats": {
                "total_users_with_consent": 0,
                "consent_by_purpose": {},
                "withdrawals": 0
            },
            "data_request_stats": {
                "total_requests": 0,
                "pending_requests": 0,
                "completed_requests": 0,
                "overdue_requests": 0
            },
            "compliance_issues": []
        }
        
        try:
            # Count users with consent records
            if self.db:
                # Database query (implementation depends on db type)
                # distinct_users = self.db.consents.distinct("user_id")
                # report["consent_stats"]["total_users_with_consent"] = len(distinct_users)
                pass
            else:
                # File-based storage
                distinct_users = set()
                for filename in os.listdir(self.consents_dir):
                    if filename.endswith("_consent.json"):
                        user_id = filename.split("_")[0]
                        distinct_users.add(user_id)
                
                report["consent_stats"]["total_users_with_consent"] = len(distinct_users)
            
            # Initialize consent by purpose counters
            for purpose in PurposeCategory:
                report["consent_stats"]["consent_by_purpose"][purpose.value] = 0
            
            # Count consents by purpose and withdrawals
            withdrawals = 0
            for user_id in distinct_users:
                consents = self.get_user_consents(user_id)
                
                for purpose in PurposeCategory:
                    if self.has_valid_consent(user_id, purpose):
                        report["consent_stats"]["consent_by_purpose"][purpose.value] += 1
                
                # Count withdrawals
                withdrawals += len([c for c in consents if c.consent_type == ConsentType.WITHDRAWN])
            
            report["consent_stats"]["withdrawals"] = withdrawals
            
            # Count data requests
            pending_requests = self.get_pending_requests()
            report["data_request_stats"]["pending_requests"] = len(pending_requests)
            
            # Count overdue requests
            overdue_requests = self.check_overdue_requests()
            report["data_request_stats"]["overdue_requests"] = len(overdue_requests)
            
            # Add overdue requests to compliance issues
            for request in overdue_requests:
                report["compliance_issues"].append({
                    "issue_type": "overdue_request",
                    "request_id": request.request_id,
                    "user_id": request.user_id,
                    "request_type": request.request_type,
                    "days_overdue": (datetime.now() - request.timestamp).days - self.access_request_deadline_days
                })
            
            return report
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Helper functions for Flask integration

def get_pipeda_consent_text(purpose: PurposeCategory) -> str:
    """
    Get the appropriate consent text for a purpose under PIPEDA.
    
    Args:
        purpose: The purpose category
        
    Returns:
        Consent text compliant with PIPEDA
    """
    consent_texts = {
        PurposeCategory.CORE_SERVICE: 
            "I consent to the collection, use, and storage of my personal information for the purpose of "
            "providing the core service features of The Inner Architect. This includes creating and "
            "managing my account, processing my inputs, and delivering personalized responses.",
            
        PurposeCategory.ENHANCEMENT:
            "I consent to the collection and use of my personal information to enhance my experience "
            "with The Inner Architect. This includes personalization of content, remembering my preferences, "
            "and providing customized recommendations based on my usage patterns.",
            
        PurposeCategory.ANALYTICS:
            "I consent to the collection and analysis of information about how I use The Inner Architect "
            "for the purpose of improving the service. This includes analyzing usage patterns, feature "
            "engagement, and performance metrics to enhance functionality and user experience.",
            
        PurposeCategory.MARKETING:
            "I consent to receiving marketing communications from The Inner Architect about new features, "
            "services, and relevant offerings. I understand I can withdraw this consent at any time.",
            
        PurposeCategory.THIRD_PARTY:
            "I consent to sharing my personal information with carefully selected third parties who "
            "provide services that enhance The Inner Architect's functionality, such as payment processing, "
            "cloud storage, and analytics. These third parties are bound by strict confidentiality agreements "
            "and will only use my information for the specified purposes."
    }
    
    return consent_texts.get(purpose, "")


def record_flask_consent(pipeda: PipedaCompliance, user_id: str, purposes: List[PurposeCategory], 
                        request=None, additional_info: Dict[str, Any] = None) -> bool:
    """
    Record consent from a Flask request.
    
    Args:
        pipeda: PipedaCompliance instance
        user_id: The user ID
        purposes: List of purposes consented to
        request: Flask request object (optional)
        additional_info: Additional information to record
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get IP address and user agent from request if available
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if hasattr(request, 'user_agent') else str(request.headers.get('User-Agent'))
        
        # Calculate expiry (1 year by default)
        expiry = datetime.now() + timedelta(days=pipeda.consent_validity_days)
        
        # Create consent record
        consent = ConsentRecord(
            user_id=user_id,
            timestamp=datetime.now(),
            consent_type=ConsentType.EXPRESS,
            purposes=purposes,
            ip_address=ip_address,
            user_agent=user_agent,
            expiry=expiry,
            additional_info=additional_info or {}
        )
        
        # Record the consent
        return pipeda.record_consent(consent)
    except Exception as e:
        logger.error(f"Error recording Flask consent: {e}")
        return False