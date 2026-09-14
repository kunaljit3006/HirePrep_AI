from typing import List, Dict, Any
from app.models.conversational_state import BehaviorStrategy

class BehaviorValidator:
    """
    Validates and resolves conflicts in behavioral strategies deterministically.
    """
    def __init__(self):
        pass

    def validate_and_resolve(self, 
                             proposed_behaviors: List[str], 
                             candidate_state: Dict[str, Any], 
                             recent_behaviors: List[str]) -> List[str]:
        
        # 1. Map to Enums and filter invalid
        valid_behaviors = []
        for b in proposed_behaviors:
            try:
                valid_behaviors.append(BehaviorStrategy(b.upper()))
            except ValueError:
                pass # Ignore invalid behaviors
                
        # If no valid behaviors or NO_SPECIAL_BEHAVIOR is present
        if not valid_behaviors or BehaviorStrategy.NO_SPECIAL_BEHAVIOR in valid_behaviors:
            return [BehaviorStrategy.NO_SPECIAL_BEHAVIOR.value]
            
        # 2. Cooldown Mechanism
        # Prevent repetitive behaviors (e.g. if ENCOURAGE was used in the last turn, don't use it again immediately)
        if len(recent_behaviors) > 0:
            last_behavior = recent_behaviors[-1]
            if last_behavior == BehaviorStrategy.ENCOURAGE.value and BehaviorStrategy.ENCOURAGE in valid_behaviors:
                valid_behaviors.remove(BehaviorStrategy.ENCOURAGE)
                
        # 3. Conflict Resolution
        has_simplify = BehaviorStrategy.SIMPLIFY in valid_behaviors
        has_challenge = BehaviorStrategy.CHALLENGE in valid_behaviors
        has_probe = BehaviorStrategy.PROBE_DEEPER in valid_behaviors
        
        if has_simplify and (has_challenge or has_probe):
            # Resolve based on candidate state
            mastery = candidate_state.get("current_mastery", "average").lower()
            performance = candidate_state.get("cumulative_performance", "average").lower()
            current_score = candidate_state.get("current_answer_score", 75.0)
            
            is_struggling = mastery == "struggling" or performance == "struggling" or current_score < 40.0
            is_strong = mastery == "excelling" or performance == "excelling"
            
            if is_struggling:
                # SIMPLIFY wins
                if has_challenge: valid_behaviors.remove(BehaviorStrategy.CHALLENGE)
                if has_probe: valid_behaviors.remove(BehaviorStrategy.PROBE_DEEPER)
            elif is_strong:
                # CHALLENGE / PROBE_DEEPER wins
                valid_behaviors.remove(BehaviorStrategy.SIMPLIFY)
            else:
                # Default for average: favor SIMPLIFY if it was explicitly asked for alongside CHALLENGE?
                # Actually, if average, maybe just PROBE_DEEPER instead of CHALLENGE. Let's let SIMPLIFY win to be safe.
                if has_challenge: valid_behaviors.remove(BehaviorStrategy.CHALLENGE)
                if has_probe: valid_behaviors.remove(BehaviorStrategy.PROBE_DEEPER)
                
        # 4. Enforce Score-Based Fallbacks (Weak Answer Rule)
        current_score = candidate_state.get("current_answer_score", 75.0)
        if current_score < 40.0:
            # Force SIMPLIFY and strip CHALLENGE/PROBE_DEEPER if they exist
            if BehaviorStrategy.CHALLENGE in valid_behaviors:
                valid_behaviors.remove(BehaviorStrategy.CHALLENGE)
            if BehaviorStrategy.PROBE_DEEPER in valid_behaviors:
                valid_behaviors.remove(BehaviorStrategy.PROBE_DEEPER)
            if BehaviorStrategy.SIMPLIFY not in valid_behaviors:
                valid_behaviors.append(BehaviorStrategy.SIMPLIFY)
                
        # 5. Enforce Strong Answer Rule
        if current_score > 85.0 and BehaviorStrategy.CHALLENGE not in valid_behaviors and BehaviorStrategy.PROBE_DEEPER not in valid_behaviors:
            # If they got a 90+, ensure we at least probe deeper or challenge
            pass # (The LLM should propose this, but we won't force append it blindly to avoid overriding natural transitions)
                
        # If valid_behaviors is empty after pruning
        if not valid_behaviors:
            return [BehaviorStrategy.NO_SPECIAL_BEHAVIOR.value]
            
        return [b.value for b in valid_behaviors]
