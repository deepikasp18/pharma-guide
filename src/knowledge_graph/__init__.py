# Knowledge Graph Components
from .patient_context_manager import PatientContextManager, ContextLayer, ContextUpdate
from .interaction_detector import (
    InteractionDetector, 
    InteractionResult, 
    ContraindicationResult,
    InteractionAnalysis,
    initialize_interaction_detector
)
from .alternative_recommender import (
    AlternativeRecommender,
    AlternativeMedication,
    ManagementStrategy,
    AlternativeRecommendation,
    initialize_alternative_recommender
)

__all__ = [
    'PatientContextManager', 
    'ContextLayer', 
    'ContextUpdate',
    'InteractionDetector',
    'InteractionResult',
    'ContraindicationResult',
    'InteractionAnalysis',
    'initialize_interaction_detector',
    'AlternativeRecommender',
    'AlternativeMedication',
    'ManagementStrategy',
    'AlternativeRecommendation',
    'initialize_alternative_recommender'
]
