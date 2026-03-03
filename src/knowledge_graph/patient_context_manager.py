"""
Patient context management for PharmaGuide
Implements patient context layer application to graph queries and dynamic updates
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .models import PatientContext
from .database import KnowledgeGraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class ContextLayer:
    """Represents a context layer applied to graph queries"""
    patient_id: str
    filters: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContextUpdate:
    """Represents an update to patient context"""
    update_id: str
    patient_id: str
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_reevaluation: bool = True


class PatientContextManager:
    """
    Manages patient context and applies personalization layers to graph queries
    
    Implements:
    - Patient context storage and retrieval
    - Context layer application to graph queries
    - Dynamic context updates and re-evaluation
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        """
        Initialize patient context manager
        
        Args:
            database: Knowledge graph database connection
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
        self._context_cache: Dict[str, PatientContext] = {}
        self._context_layers: Dict[str, ContextLayer] = {}
        self._update_history: List[ContextUpdate] = []
    
    async def create_patient_context(
        self,
        demographics: Dict[str, Any],
        conditions: Optional[List[str]] = None,
        medications: Optional[List[Dict[str, Any]]] = None,
        allergies: Optional[List[str]] = None,
        genetic_factors: Optional[Dict[str, Any]] = None,
        risk_factors: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> PatientContext:
        """
        Create a new patient context
        
        Args:
            demographics: Patient demographics (age, gender, weight, height)
            conditions: Current medical conditions
            medications: Current medications with dosing
            allergies: Known drug allergies
            genetic_factors: Pharmacogenomic information
            risk_factors: Clinical and lifestyle risks
            preferences: User preferences and settings
            
        Returns:
            Created PatientContext
        """
        try:
            patient_id = str(uuid.uuid4())
            
            patient_context = PatientContext(
                id=patient_id,
                demographics=demographics or {},
                conditions=conditions or [],
                medications=medications or [],
                allergies=allergies or [],
                genetic_factors=genetic_factors or {},
                risk_factors=risk_factors or [],
                preferences=preferences or {}
            )
            
            # Store in database
            await self.db.create_patient_vertex(patient_context)
            
            # Cache the context
            self._context_cache[patient_id] = patient_context
            
            # Create initial context layer
            context_layer = self._create_context_layer(patient_context)
            self._context_layers[patient_id] = context_layer
            
            self.logger.info(f"Created patient context: {patient_id}")
            return patient_context
            
        except Exception as e:
            self.logger.error(f"Error creating patient context: {e}")
            raise
    
    async def get_patient_context(self, patient_id: str) -> Optional[PatientContext]:
        """
        Retrieve patient context by ID
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            PatientContext if found, None otherwise
        """
        try:
            # Check cache first
            if patient_id in self._context_cache:
                return self._context_cache[patient_id]
            
            # Query database
            g = self.db.connection.g
            result = g.V().has('id', patient_id).hasLabel('Patient').valueMap(True).toList()
            
            if not result:
                self.logger.warning(f"Patient context not found: {patient_id}")
                return None
            
            # Parse result into PatientContext
            patient_data = result[0]
            patient_context = self._parse_patient_from_graph(patient_data)
            
            # Cache it
            self._context_cache[patient_id] = patient_context
            
            return patient_context
            
        except Exception as e:
            self.logger.error(f"Error retrieving patient context: {e}")
            return None
    
    async def update_patient_context(
        self,
        patient_id: str,
        updates: Dict[str, Any]
    ) -> Optional[PatientContext]:
        """
        Update patient context and trigger re-evaluation
        
        Args:
            patient_id: Patient identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated PatientContext
        """
        try:
            # Get current context
            current_context = await self.get_patient_context(patient_id)
            if not current_context:
                self.logger.error(f"Cannot update non-existent patient: {patient_id}")
                return None
            
            # Track updates for re-evaluation
            context_updates = []
            
            # Apply updates
            for field, new_value in updates.items():
                if hasattr(current_context, field):
                    old_value = getattr(current_context, field)
                    
                    # Record update
                    update = ContextUpdate(
                        update_id=str(uuid.uuid4()),
                        patient_id=patient_id,
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                        requires_reevaluation=self._requires_reevaluation(field)
                    )
                    context_updates.append(update)
                    self._update_history.append(update)
                    
                    # Apply update
                    setattr(current_context, field, new_value)
            
            # Update timestamp
            current_context.updated_at = datetime.utcnow()
            
            # Update in database
            await self._update_patient_in_database(current_context)
            
            # Update cache
            self._context_cache[patient_id] = current_context
            
            # Update context layer
            context_layer = self._create_context_layer(current_context)
            self._context_layers[patient_id] = context_layer
            
            # Trigger re-evaluation if needed
            if any(u.requires_reevaluation for u in context_updates):
                await self._trigger_reevaluation(patient_id, context_updates)
            
            self.logger.info(
                f"Updated patient context: {patient_id}, "
                f"fields: {list(updates.keys())}"
            )
            
            return current_context
            
        except Exception as e:
            self.logger.error(f"Error updating patient context: {e}")
            return None
    
    def get_context_layer(self, patient_id: str) -> Optional[ContextLayer]:
        """
        Get context layer for patient
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            ContextLayer if exists
        """
        return self._context_layers.get(patient_id)
    
    def apply_context_to_query(
        self,
        query_params: Dict[str, Any],
        patient_id: str
    ) -> Dict[str, Any]:
        """
        Apply patient context layer to graph query parameters
        
        Args:
            query_params: Base query parameters
            patient_id: Patient identifier
            
        Returns:
            Query parameters with context applied
        """
        try:
            context_layer = self.get_context_layer(patient_id)
            if not context_layer or not context_layer.active:
                return query_params
            
            # Create contextualized query params
            contextualized = query_params.copy()
            
            # Apply filters from context layer
            if 'filters' not in contextualized:
                contextualized['filters'] = {}
            
            contextualized['filters'].update(context_layer.filters)
            
            # Apply weights from context layer
            if 'weights' not in contextualized:
                contextualized['weights'] = {}
            
            contextualized['weights'].update(context_layer.weights)
            
            # Add patient context metadata
            contextualized['patient_id'] = patient_id
            contextualized['context_applied'] = True
            
            self.logger.debug(f"Applied context layer for patient: {patient_id}")
            
            return contextualized
            
        except Exception as e:
            self.logger.error(f"Error applying context to query: {e}")
            return query_params
    
    async def add_medication(
        self,
        patient_id: str,
        medication: Dict[str, Any]
    ) -> bool:
        """
        Add medication to patient context
        
        Args:
            patient_id: Patient identifier
            medication: Medication details (name, dosage, frequency, etc.)
            
        Returns:
            True if successful
        """
        try:
            context = await self.get_patient_context(patient_id)
            if not context:
                return False
            
            # Add medication
            context.medications.append(medication)
            
            # Update context
            await self.update_patient_context(
                patient_id,
                {'medications': context.medications}
            )
            
            self.logger.info(
                f"Added medication to patient {patient_id}: "
                f"{medication.get('name', 'unknown')}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding medication: {e}")
            return False
    
    async def remove_medication(
        self,
        patient_id: str,
        medication_name: str
    ) -> bool:
        """
        Remove medication from patient context
        
        Args:
            patient_id: Patient identifier
            medication_name: Name of medication to remove
            
        Returns:
            True if successful
        """
        try:
            context = await self.get_patient_context(patient_id)
            if not context:
                return False
            
            # Remove medication
            context.medications = [
                med for med in context.medications
                if med.get('name', '').lower() != medication_name.lower()
            ]
            
            # Update context
            await self.update_patient_context(
                patient_id,
                {'medications': context.medications}
            )
            
            self.logger.info(
                f"Removed medication from patient {patient_id}: {medication_name}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing medication: {e}")
            return False
    
    async def add_condition(
        self,
        patient_id: str,
        condition: str
    ) -> bool:
        """
        Add medical condition to patient context
        
        Args:
            patient_id: Patient identifier
            condition: Medical condition
            
        Returns:
            True if successful
        """
        try:
            context = await self.get_patient_context(patient_id)
            if not context:
                return False
            
            # Add condition if not already present
            if condition not in context.conditions:
                context.conditions.append(condition)
                
                # Update context
                await self.update_patient_context(
                    patient_id,
                    {'conditions': context.conditions}
                )
                
                self.logger.info(
                    f"Added condition to patient {patient_id}: {condition}"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding condition: {e}")
            return False
    
    async def remove_condition(
        self,
        patient_id: str,
        condition: str
    ) -> bool:
        """
        Remove medical condition from patient context
        
        Args:
            patient_id: Patient identifier
            condition: Medical condition to remove
            
        Returns:
            True if successful
        """
        try:
            context = await self.get_patient_context(patient_id)
            if not context:
                return False
            
            # Remove condition
            if condition in context.conditions:
                context.conditions.remove(condition)
                
                # Update context
                await self.update_patient_context(
                    patient_id,
                    {'conditions': context.conditions}
                )
                
                self.logger.info(
                    f"Removed condition from patient {patient_id}: {condition}"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing condition: {e}")
            return False
    
    def get_update_history(
        self,
        patient_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ContextUpdate]:
        """
        Get context update history
        
        Args:
            patient_id: Optional patient ID to filter by
            limit: Maximum number of updates to return
            
        Returns:
            List of context updates
        """
        updates = self._update_history
        
        if patient_id:
            updates = [u for u in updates if u.patient_id == patient_id]
        
        # Sort by timestamp (most recent first)
        updates = sorted(updates, key=lambda u: u.timestamp, reverse=True)
        
        return updates[:limit]
    
    def _create_context_layer(self, patient_context: PatientContext) -> ContextLayer:
        """
        Create context layer from patient context
        
        Args:
            patient_context: Patient context
            
        Returns:
            ContextLayer with filters and weights
        """
        filters = {}
        weights = {}
        
        # Demographics filters
        demographics = patient_context.demographics
        if demographics:
            age = demographics.get('age')
            if age:
                filters['age'] = age
                # Weight adjustments for age
                if age > 65:
                    weights['age_risk'] = 1.2
                elif age < 18:
                    weights['age_risk'] = 1.15
                else:
                    weights['age_risk'] = 1.0
            
            gender = demographics.get('gender')
            if gender:
                filters['gender'] = gender
        
        # Condition filters
        if patient_context.conditions:
            filters['conditions'] = patient_context.conditions
            # Increase weight for patients with multiple conditions
            weights['condition_risk'] = 1.0 + (len(patient_context.conditions) * 0.05)
        
        # Medication filters
        if patient_context.medications:
            medication_names = [
                med.get('name', '') for med in patient_context.medications
            ]
            filters['current_medications'] = medication_names
            # Polypharmacy weight
            if len(patient_context.medications) > 5:
                weights['polypharmacy_risk'] = 1.1
        
        # Allergy filters
        if patient_context.allergies:
            filters['allergies'] = patient_context.allergies
            weights['allergy_risk'] = 1.2
        
        # Risk factor weights
        if patient_context.risk_factors:
            weights['risk_factors'] = 1.0 + (len(patient_context.risk_factors) * 0.03)
        
        return ContextLayer(
            patient_id=patient_context.id,
            filters=filters,
            weights=weights,
            active=True
        )
    
    def _requires_reevaluation(self, field: str) -> bool:
        """
        Determine if field update requires re-evaluation
        
        Args:
            field: Field name that was updated
            
        Returns:
            True if re-evaluation needed
        """
        # Fields that require re-evaluation
        critical_fields = {
            'medications',
            'conditions',
            'allergies',
            'demographics',
            'risk_factors'
        }
        
        return field in critical_fields
    
    async def _trigger_reevaluation(
        self,
        patient_id: str,
        updates: List[ContextUpdate]
    ) -> None:
        """
        Trigger re-evaluation of patient context
        
        Args:
            patient_id: Patient identifier
            updates: List of context updates
        """
        try:
            self.logger.info(
                f"Triggering re-evaluation for patient {patient_id} "
                f"due to {len(updates)} critical updates"
            )
            
            # Get updated context
            context = await self.get_patient_context(patient_id)
            if not context:
                return
            
            # Re-create context layer with updated information
            context_layer = self._create_context_layer(context)
            self._context_layers[patient_id] = context_layer
            
            # Log re-evaluation
            self.logger.info(
                f"Re-evaluation complete for patient {patient_id}. "
                f"Updated filters: {list(context_layer.filters.keys())}, "
                f"Updated weights: {list(context_layer.weights.keys())}"
            )
            
        except Exception as e:
            self.logger.error(f"Error triggering re-evaluation: {e}")
    
    async def _update_patient_in_database(
        self,
        patient_context: PatientContext
    ) -> None:
        """
        Update patient context in database
        
        Args:
            patient_context: Updated patient context
        """
        try:
            g = self.db.connection.g
            
            # Update vertex properties
            import json
            
            traversal = g.V().has('id', patient_context.id)
            
            # Update each field
            for field, value in patient_context.model_dump().items():
                if field == 'id':
                    continue
                
                if isinstance(value, (list, dict)):
                    traversal = traversal.property(field, json.dumps(value))
                else:
                    traversal = traversal.property(field, str(value))
            
            traversal.toList()
            
            self.logger.debug(f"Updated patient in database: {patient_context.id}")
            
        except Exception as e:
            self.logger.error(f"Error updating patient in database: {e}")
            raise
    
    def _parse_patient_from_graph(
        self,
        graph_data: Dict[str, Any]
    ) -> PatientContext:
        """
        Parse patient context from graph data
        
        Args:
            graph_data: Raw graph data
            
        Returns:
            PatientContext
        """
        import json
        
        # Extract and parse fields
        patient_id = graph_data.get('id', '')
        
        demographics_str = graph_data.get('demographics', '{}')
        demographics = json.loads(demographics_str) if isinstance(demographics_str, str) else demographics_str
        
        conditions_str = graph_data.get('conditions', '[]')
        conditions = json.loads(conditions_str) if isinstance(conditions_str, str) else conditions_str
        
        medications_str = graph_data.get('medications', '[]')
        medications = json.loads(medications_str) if isinstance(medications_str, str) else medications_str
        
        allergies_str = graph_data.get('allergies', '[]')
        allergies = json.loads(allergies_str) if isinstance(allergies_str, str) else allergies_str
        
        genetic_factors_str = graph_data.get('genetic_factors', '{}')
        genetic_factors = json.loads(genetic_factors_str) if isinstance(genetic_factors_str, str) else genetic_factors_str
        
        risk_factors_str = graph_data.get('risk_factors', '[]')
        risk_factors = json.loads(risk_factors_str) if isinstance(risk_factors_str, str) else risk_factors_str
        
        preferences_str = graph_data.get('preferences', '{}')
        preferences = json.loads(preferences_str) if isinstance(preferences_str, str) else preferences_str
        
        return PatientContext(
            id=patient_id,
            demographics=demographics,
            conditions=conditions,
            medications=medications,
            allergies=allergies,
            genetic_factors=genetic_factors,
            risk_factors=risk_factors,
            preferences=preferences
        )
