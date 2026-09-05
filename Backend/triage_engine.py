# backend/triage_engine.py

def calculate_news2_score(heart_rate: int, spo2: int, sys_bp: int) -> dict:
    """
    Evaluates vital signs using simplified NEWS2 (National Early Warning Score) clinical thresholds.
    """
    score = 0
    
    # Heart Rate Scoring
    if heart_rate <= 40 or heart_rate >= 131:
        score += 3
    elif heart_rate >= 111 or heart_rate <= 50:
        score += 2
    elif heart_rate >= 91:
        score += 1
        
    # SpO2 Scoring (Oxygen Saturation)
    if spo2 <= 91:
        score += 3
    elif spo2 in [92, 93]:
        score += 2
    elif spo2 in [94, 95]:
        score += 1
        
    # Systolic BP Scoring
    if sys_bp <= 90 or sys_bp >= 220:
        score += 3
    elif sys_bp <= 100:
        score += 2
    elif sys_bp <= 110:
        score += 1

    # Triage Level Assignment
    if score >= 5:
        priority = "RED - IMMEDIATE EMERGENCY"
    elif score >= 3:
        priority = "YELLOW - URGENT ATTENTION"
    else:
        priority = "GREEN - ROUTINE MONITORING"
        
    return {
        "news2_score": score,
        "triage_priority": priority
    }