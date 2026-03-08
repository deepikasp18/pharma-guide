"""
In-memory drug database for production use
Contains common medications with side effects, interactions, and dosing information
"""
from typing import Dict, List, Optional

# Drug database with side effects
DRUG_DATABASE = {
    "aspirin": {
        "name": "Aspirin",
        "generic_name": "acetylsalicylic acid",
        "class": "NSAID",
        "side_effects": [
            {
                "name": "Stomach upset",
                "severity": "moderate",
                "frequency": "common (10-25%)",
                "description": "May cause stomach discomfort, nausea, or indigestion",
                "management": "Take with food or milk to reduce stomach irritation"
            },
            {
                "name": "Bleeding risk",
                "severity": "major",
                "frequency": "uncommon (1-10%)",
                "description": "Increased risk of bleeding, especially with prolonged use",
                "management": "Monitor for unusual bruising or bleeding; consult doctor if occurs"
            },
            {
                "name": "Allergic reaction",
                "severity": "major",
                "frequency": "rare (<1%)",
                "description": "May cause rash, itching, swelling, or difficulty breathing",
                "management": "Seek immediate medical attention if allergic symptoms occur"
            },
            {
                "name": "Ringing in ears",
                "severity": "minor",
                "frequency": "uncommon (1-10%)",
                "description": "Tinnitus or ringing sensation in the ears",
                "management": "Usually resolves when medication is stopped"
            }
        ],
        "interactions": ["warfarin", "ibuprofen", "methotrexate"],
        "dosing": {
            "pain_relief": "325-650 mg every 4-6 hours as needed",
            "max_daily": "4000 mg",
            "cardiovascular": "81-325 mg once daily"
        }
    },
    "lisinopril": {
        "name": "Lisinopril",
        "generic_name": "lisinopril",
        "class": "ACE Inhibitor",
        "side_effects": [
            {
                "name": "Dry cough",
                "severity": "minor",
                "frequency": "common (10-20%)",
                "description": "Persistent dry cough is a common side effect",
                "management": "May resolve over time; consult doctor if bothersome"
            },
            {
                "name": "Dizziness",
                "severity": "moderate",
                "frequency": "common (5-10%)",
                "description": "May cause lightheadedness, especially when standing up",
                "management": "Rise slowly from sitting or lying position"
            },
            {
                "name": "High potassium",
                "severity": "major",
                "frequency": "uncommon (1-5%)",
                "description": "Can cause elevated potassium levels in blood",
                "management": "Regular blood tests to monitor potassium levels"
            },
            {
                "name": "Angioedema",
                "severity": "critical",
                "frequency": "rare (<0.1%)",
                "description": "Severe swelling of face, lips, tongue, or throat",
                "management": "Seek emergency medical attention immediately"
            }
        ],
        "interactions": ["potassium supplements", "nsaids", "lithium"],
        "dosing": {
            "hypertension": "10-40 mg once daily",
            "heart_failure": "5-40 mg once daily",
            "initial": "Start with 5-10 mg once daily"
        }
    },
    "metformin": {
        "name": "Metformin",
        "generic_name": "metformin",
        "class": "Biguanide",
        "side_effects": [
            {
                "name": "Diarrhea",
                "severity": "moderate",
                "frequency": "very common (>25%)",
                "description": "Gastrointestinal upset, especially when starting treatment",
                "management": "Take with meals; usually improves over time"
            },
            {
                "name": "Nausea",
                "severity": "moderate",
                "frequency": "common (10-25%)",
                "description": "Feeling of nausea, especially in first few weeks",
                "management": "Take with food; start with low dose and increase gradually"
            },
            {
                "name": "Vitamin B12 deficiency",
                "severity": "moderate",
                "frequency": "uncommon (5-10%)",
                "description": "Long-term use may reduce B12 absorption",
                "management": "Regular B12 level monitoring; supplementation if needed"
            },
            {
                "name": "Lactic acidosis",
                "severity": "critical",
                "frequency": "very rare (<0.01%)",
                "description": "Serious metabolic complication",
                "management": "Seek immediate medical attention if symptoms occur"
            }
        ],
        "interactions": ["alcohol", "contrast dye", "cimetidine"],
        "dosing": {
            "initial": "500 mg twice daily or 850 mg once daily with meals",
            "maintenance": "1000-2000 mg daily in divided doses",
            "max_daily": "2550 mg"
        }
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "generic_name": "ibuprofen",
        "class": "NSAID",
        "side_effects": [
            {
                "name": "Stomach pain",
                "severity": "moderate",
                "frequency": "common (10-20%)",
                "description": "Abdominal pain, heartburn, or upset stomach",
                "management": "Take with food or milk"
            },
            {
                "name": "Increased blood pressure",
                "severity": "moderate",
                "frequency": "uncommon (1-10%)",
                "description": "May raise blood pressure in some individuals",
                "management": "Monitor blood pressure regularly"
            },
            {
                "name": "Kidney problems",
                "severity": "major",
                "frequency": "rare (<1%)",
                "description": "Can affect kidney function with prolonged use",
                "management": "Stay hydrated; regular kidney function tests"
            },
            {
                "name": "Cardiovascular events",
                "severity": "critical",
                "frequency": "rare (<1%)",
                "description": "Increased risk of heart attack or stroke with long-term use",
                "management": "Use lowest effective dose for shortest duration"
            }
        ],
        "interactions": ["aspirin", "warfarin", "ace inhibitors"],
        "dosing": {
            "pain": "200-400 mg every 4-6 hours as needed",
            "inflammation": "400-800 mg three times daily",
            "max_daily": "3200 mg"
        }
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "generic_name": "atorvastatin",
        "class": "Statin",
        "side_effects": [
            {
                "name": "Muscle pain",
                "severity": "moderate",
                "frequency": "common (5-10%)",
                "description": "Muscle aches, pain, or weakness",
                "management": "Report to doctor; may need dose adjustment"
            },
            {
                "name": "Liver enzyme elevation",
                "severity": "moderate",
                "frequency": "uncommon (1-3%)",
                "description": "Elevated liver enzymes in blood tests",
                "management": "Regular liver function monitoring"
            },
            {
                "name": "Digestive problems",
                "severity": "minor",
                "frequency": "common (5-10%)",
                "description": "Nausea, gas, or constipation",
                "management": "Usually mild and temporary"
            },
            {
                "name": "Rhabdomyolysis",
                "severity": "critical",
                "frequency": "very rare (<0.01%)",
                "description": "Severe muscle breakdown",
                "management": "Seek immediate medical attention for severe muscle pain"
            }
        ],
        "interactions": ["grapefruit juice", "gemfibrozil", "cyclosporine"],
        "dosing": {
            "initial": "10-20 mg once daily",
            "maintenance": "10-80 mg once daily",
            "max_daily": "80 mg"
        }
    }
}

# Drug interaction database
DRUG_INTERACTIONS = {
    ("aspirin", "warfarin"): {
        "severity": "major",
        "description": "Increased risk of bleeding when combined. Close monitoring required.",
        "mechanism": "Both drugs affect blood clotting",
        "management": "Avoid combination if possible; if necessary, monitor INR closely"
    },
    ("aspirin", "ibuprofen"): {
        "severity": "moderate",
        "description": "May increase risk of gastrointestinal bleeding",
        "mechanism": "Additive effects on stomach lining",
        "management": "Use together only if necessary; take with food"
    },
    ("lisinopril", "ibuprofen"): {
        "severity": "moderate",
        "description": "NSAIDs may reduce effectiveness of ACE inhibitors",
        "mechanism": "Prostaglandin inhibition affects blood pressure control",
        "management": "Monitor blood pressure; consider alternative pain reliever"
    },
    ("metformin", "alcohol"): {
        "severity": "major",
        "description": "Increased risk of lactic acidosis",
        "mechanism": "Both affect lactate metabolism",
        "management": "Avoid excessive alcohol consumption"
    }
}


class DrugDatabase:
    """In-memory drug database for quick lookups"""
    
    def __init__(self):
        self.drugs = DRUG_DATABASE
        self.interactions = DRUG_INTERACTIONS
    
    def search_drug(self, query: str) -> Optional[Dict]:
        """Search for a drug by name (case-insensitive)"""
        query_lower = query.lower().strip()
        
        # Direct match
        if query_lower in self.drugs:
            return self.drugs[query_lower]
        
        # Partial match
        for drug_key, drug_data in self.drugs.items():
            if query_lower in drug_key or query_lower in drug_data["name"].lower():
                return drug_data
        
        return None
    
    def get_side_effects(self, drug_name: str) -> List[Dict]:
        """Get side effects for a drug"""
        drug = self.search_drug(drug_name)
        if drug:
            return drug.get("side_effects", [])
        return []
    
    def get_interactions(self, drug1: str, drug2: str) -> Optional[Dict]:
        """Get interaction between two drugs"""
        drug1_lower = drug1.lower().strip()
        drug2_lower = drug2.lower().strip()
        
        # Check both orderings
        interaction = self.interactions.get((drug1_lower, drug2_lower))
        if not interaction:
            interaction = self.interactions.get((drug2_lower, drug1_lower))
        
        return interaction
    
    def get_dosing(self, drug_name: str) -> Optional[Dict]:
        """Get dosing information for a drug"""
        drug = self.search_drug(drug_name)
        if drug:
            return drug.get("dosing", {})
        return None
    
    def list_all_drugs(self) -> List[str]:
        """List all available drugs"""
        return [drug["name"] for drug in self.drugs.values()]


# Global instance
drug_db = DrugDatabase()
