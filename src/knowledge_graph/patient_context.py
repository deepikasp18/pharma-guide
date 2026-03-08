"""
Patient context management for personalized medication queries
Implements context layer application to graph queries and dynamic updates
"""
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class ContextFilter:
    """Represents a filter derived from patient context"""
    filter_type: str  # 'age', 'condition', 'medication', 'allergy', 'genetic'
    property_name: str
    operator: str  # 'eq', 'gte', 'lte', 'in', 'not_in'
    value: Any
    confidence: float = 1.0


@dataclass
class ContextUpdate:
    """Represents a change to patient context"""
    update_type: str  # 'add', 'remove', 'modify'
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    requires_reevaluation: bool


class PatientContextManager:
    """
    Manages patient context and applies it to knowledge graph queries
    Supports dynamic context updates and automatic re-evaluation
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        self._context_cache: Dict[str, PatientContext] = {}
        self._active_queries: Dict[str, List[str]] = {}  # patient_id -> query_ids
    
    async def create_patient_context(
        self,
        patient_id: str,
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
            patient_id: Unique patient identifier
            demographics: Patient demographics (age, gender, weight, height)
            conditions: List of current medical conditions
            medications: List of current medications with dosing
            allergies: List of known drug allergies
            genetic_factors: Pharmacogenomic information
            risk_factors: Clinical and lifestyle risk factors
            preferences: User preferences and settings
        
        Returns:
            Created PatientContext
        """
        try:
            self.logger.info(f"Creating patient context for {patient_id}")
            
            context = PatientContext(
                id=patient_id,
                demographics=demographics or {},
                conditions=conditions or [],
                medications=medications or [],
                allergies=allergies or [],
                genetic_factors=genetic_factors or {},
                risk_factors=risk_factors or [],
                preferences=preferences or {}
            )
            
            # Store in cache
            self._context_cache[patient_id] = context
            
            # Create patient vertex in knowledge graph
            await self.database.create_patient_vertex(context)
            
            self.logger.info(f"Patient context created for {patient_id}")
            return context
        
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
        # Check cache first
        if patient_id in self._context_cache:
            return self._context_cache[patient_id]
        
        # Query from database
        try:
            # In a real implementation, this would query the graph database
            self.logger.info(f"Retrieving patient context for {patient_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving patient context: {e}")
            return None
    
    async def update_patient_context(
        self,
        patient_id: str,
        updates: Dict[str, Any]
    ) -> ContextUpdate:
        """
        Update patient context and trigger re-evaluation if needed
        
        Args:
            patient_id: Patient identifier
            updates: Dictionary of fields to update
        
        Returns:
            ContextUpdate describing the changes
        """
        try:
            self.logger.info(f"Updating patient context for {patient_id}")
            
            context = await self.get_patient_context(patient_id)
            if not context:
                raise ValueError(f"Patient context not found: {patient_id}")
            
            # Track changes
            changes = []
            requires_reevaluation = False
            
            for field, new_value in updates.items():
                if hasattr(context, field):
                    old_value = getattr(context, field)
                    
                    # Check if this is a significant change
                    if self._is_significant_change(field, old_value, new_value):
                        requires_reevaluation = True
                    
                    # Update the field
                    setattr(context, field, new_value)
                    
                    changes.append(ContextUpdate(
                        update_type='modify',
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                        timestamp=datetime.utcnow(),
                        requires_reevaluation=requires_reevaluation
                    ))
            
            # Update timestamp
            context.updated_at = datetime.utcnow()
            
            # Update cache
            self._context_cache[patient_id] = context
            
            # Trigger re-evaluation if needed
            if requires_reevaluation:
                await self._trigger_reevaluation(patient_id, context)
            
            self.logger.info(
                f"Patient context updated for {patient_id}, "
                f"re-evaluation required: {requires_reevaluation}"
            )
            
            return changes[0] if changes else ContextUpdate(
                update_type='modify',
                field='none',
                old_value=None,
                new_value=None,
                timestamp=datetime.utcnow(),
                requires_reevaluation=False
            )
        
        except Exception as e:
            self.logger.error(f"Error updating patient context: {e}")
            raise
    
    def apply_context_to_query(
        self,
        base_query: str,
        patient_context: PatientContext,
        query_intent: str
    ) -> str:
        """
        Apply patient context as filters to a graph query
        
        Args:
            base_query: Base Gremlin query string
            patient_context: Patient context to apply
            query_intent: Intent of the query (side_effects, interactions, etc.)
        
        Returns:
            Modified query with context filters applied
        """
        try:
            self.logger.info(f"Applying patient context to {query_intent} query")
            
            # Extract context filters
            filters = self._extract_context_filters(patient_context, query_intent)
            
            # Apply filters to query
            modified_query = self._apply_filters_to_query(base_query, filters)
            
            self.logger.info(f"Applied {len(filters)} context filters to query")
            return modified_query
        
        except Exception as e:
            self.logger.error(f"Error applying context to query: {e}")
            return base_query  # Return unmodified query on error
    
    def _extract_context_filters(
        self,
        patient_context: PatientContext,
        query_intent: str
    ) -> List[ContextFilter]:
        """Extract relevant filters from patient context based on query intent"""
        filters = []
        
        # Age-based filters
        if 'age' in patient_context.demographics:
            age = patient_context.demographics['age']
            filters.append(ContextFilter(
                filter_type='age',
                property_name='age_relevance',
                operator='gte',
                value=0.5 if age >= 65 or age < 18 else 0.3,
                confidence=1.0
            ))
        
        # Condition-based filters
        if patient_context.conditions:
            filters.append(ContextFilter(
                filter_type='condition',
                property_name='contraindicated_conditions',
                operator='not_in',
                value=patient_context.conditions,
                confidence=1.0
            ))
        
        # Medication interaction filters
        if patient_context.medications and query_intent in ['interactions', 'side_effects']:
            current_drug_names = [med.get('name') for med in patient_context.medications]
            filters.append(ContextFilter(
                filter_type='medication',
                property_name='interacting_drugs',
                operator='in',
                value=current_drug_names,
                confidence=0.9
            ))
        
        # Allergy filters
        if patient_context.allergies:
            filters.append(ContextFilter(
                filter_type='allergy',
                property_name='drug_name',
                operator='not_in',
                value=patient_context.allergies,
                confidence=1.0
            ))
        
        # Genetic factor filters
        if patient_context.genetic_factors and query_intent in ['dosing', 'effectiveness']:
            for gene, variant in patient_context.genetic_factors.items():
                filters.append(ContextFilter(
                    filter_type='genetic',
                    property_name=f'pharmacogenomic_{gene}',
                    operator='eq',
                    value=variant,
                    confidence=0.8
                ))
        
        # Risk factor filters
        if patient_context.risk_factors:
            # Increase confidence threshold for high-risk patients
            filters.append(ContextFilter(
                filter_type='risk',
                property_name='confidence',
                operator='gte',
                value=0.7,
                confidence=1.0
            ))
        
        return filters
    
    def _apply_filters_to_query(
        self,
        base_query: str,
        filters: List[ContextFilter]
    ) -> str:
        """Apply context filters to a Gremlin query"""
        if not filters:
            return base_query
        
        # Find insertion point (before .toList() or similar terminal step)
        terminal_steps = ['.toList()', '.toSet()', '.next()', '.iterate()']
        insertion_point = -1
        terminal_step = ''
        
        for step in terminal_steps:
            if step in base_query:
                insertion_point = base_query.rfind(step)
                terminal_step = step
                break
        
        if insertion_point == -1:
            # No terminal step found, append to end
            modified_query = base_query
        else:
            # Insert filters before terminal step
            modified_query = base_query[:insertion_point]
        
        # Add filter steps
        for filter_obj in filters:
            if filter_obj.operator == 'gte':
                modified_query += f".has('{filter_obj.property_name}', P.gte({filter_obj.value}))"
            elif filter_obj.operator == 'lte':
                modified_query += f".has('{filter_obj.property_name}', P.lte({filter_obj.value}))"
            elif filter_obj.operator == 'eq':
                modified_query += f".has('{filter_obj.property_name}', '{filter_obj.value}')"
            elif filter_obj.operator == 'in':
                value_list = ', '.join(f"'{v}'" for v in filter_obj.value)
                modified_query += f".where(__.out('INTERACTS_WITH').has('name', within({value_list})))"
            elif filter_obj.operator == 'not_in':
                value_list = ', '.join(f"'{v}'" for v in filter_obj.value)
                modified_query += f".where(__.not(__.has('name', within({value_list}))))"
        
        # Add terminal step back
        if terminal_step:
            modified_query += terminal_step
        
        return modified_query
    
    def _is_significant_change(
        self,
        field: str,
        old_value: Any,
        new_value: Any
    ) -> bool:
        """Determine if a context change requires query re-evaluation"""
        # Changes to these fields always require re-evaluation
        significant_fields = {
            'conditions', 'medications', 'allergies', 
            'genetic_factors', 'risk_factors'
        }
        
        if field in significant_fields:
            return old_value != new_value
        
        # Demographic changes
        if field == 'demographics':
            # Check for significant age changes (crossing risk thresholds)
            old_age = old_value.get('age', 0) if isinstance(old_value, dict) else 0
            new_age = new_value.get('age', 0) if isinstance(new_value, dict) else 0
            
            # Crossing 65 (elderly) or 18 (adult) thresholds
            if (old_age < 65 <= new_age) or (old_age >= 65 > new_age):
                return True
            if (old_age < 18 <= new_age) or (old_age >= 18 > new_age):
                return True
        
        return False
    
    async def _trigger_reevaluation(
        self,
        patient_id: str,
        updated_context: PatientContext
    ) -> None:
        """Trigger re-evaluation of active queries for a patient"""
        try:
            self.logger.info(f"Triggering re-evaluation for patient {patient_id}")
            
            # Get active queries for this patient
            active_queries = self._active_queries.get(patient_id, [])
            
            if not active_queries:
                self.logger.info(f"No active queries to re-evaluate for {patient_id}")
                return
            
            # Re-evaluate each active query
            for query_id in active_queries:
                self.logger.info(f"Re-evaluating query {query_id}")
                # In a real implementation, this would:
                # 1. Retrieve the original query
                # 2. Re-apply the updated context
                # 3. Execute the query
                # 4. Compare results and notify if significant changes
                # 5. Update any cached results
            
            self.logger.info(f"Re-evaluation complete for {len(active_queries)} queries")
        
        except Exception as e:
            self.logger.error(f"Error triggering re-evaluation: {e}")
    
    def register_active_query(
        self,
        patient_id: str,
        query_id: str
    ) -> None:
        """Register a query as active for a patient (for re-evaluation tracking)"""
        if patient_id not in self._active_queries:
            self._active_queries[patient_id] = []
        
        if query_id not in self._active_queries[patient_id]:
            self._active_queries[patient_id].append(query_id)
            self.logger.debug(f"Registered active query {query_id} for patient {patient_id}")
    
    def unregister_active_query(
        self,
        patient_id: str,
        query_id: str
    ) -> None:
        """Unregister an active query"""
        if patient_id in self._active_queries:
            if query_id in self._active_queries[patient_id]:
                self._active_queries[patient_id].remove(query_id)
                self.logger.debug(f"Unregistered query {query_id} for patient {patient_id}")
    
    async def calculate_personalized_risk_factors(
        self,
        patient_context: PatientContext,
        drug_id: str
    ) -> Dict[str, Any]:
        """
        Calculate personalized risk factors for a drug based on patient context
        
        Args:
            patient_context: Patient context
            drug_id: Drug identifier
        
        Returns:
            Dictionary of risk factors with scores
        """
        try:
            self.logger.info(f"Calculating personalized risk factors for drug {drug_id}")
            
            risk_factors = {
                'age_risk': 0.0,
                'comorbidity_risk': 0.0,
                'polypharmacy_risk': 0.0,
                'genetic_risk': 0.0,
                'overall_risk': 0.0
            }
            
            # Age-based risk
            age = patient_context.demographics.get('age', 0)
            if age >= 65:
                risk_factors['age_risk'] = 0.3
            elif age < 18:
                risk_factors['age_risk'] = 0.25
            
            # Comorbidity risk
            high_risk_conditions = [
                'kidney_disease', 'liver_disease', 'heart_disease',
                'diabetes', 'hypertension'
            ]
            condition_matches = sum(
                1 for condition in patient_context.conditions
                if any(hrc in condition.lower() for hrc in high_risk_conditions)
            )
            risk_factors['comorbidity_risk'] = min(condition_matches * 0.15, 0.5)
            
            # Polypharmacy risk
            med_count = len(patient_context.medications)
            if med_count > 5:
                risk_factors['polypharmacy_risk'] = min((med_count - 5) * 0.1, 0.4)
            
            # Genetic risk (if available)
            if patient_context.genetic_factors:
                # Simplified - in reality would query specific gene-drug interactions
                risk_factors['genetic_risk'] = 0.2
            
            # Calculate overall risk
            risk_factors['overall_risk'] = min(
                sum(v for k, v in risk_factors.items() if k != 'overall_risk'),
                1.0
            )
            
            self.logger.info(
                f"Calculated overall risk: {risk_factors['overall_risk']:.2f}"
            )
            
            return risk_factors
        
        except Exception as e:
            self.logger.error(f"Error calculating risk factors: {e}")
            return {'overall_risk': 0.0}


# Factory function
async def create_patient_context_manager(
    database: KnowledgeGraphDatabase
) -> PatientContextManager:
    """Create patient context manager"""
    return PatientContextManager(database)
