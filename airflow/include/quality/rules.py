from typing import Dict, Any, List, Tuple
from datetime import datetime

# Seismic & Geophysics Quality Rule Identifiers
RULE_ID_REQUIRED = "RULE_ID_REQUIRED"
RULE_TIME_REQUIRED = "RULE_TIME_REQUIRED"
RULE_COORDINATES_REQUIRED = "RULE_COORDINATES_REQUIRED"
RULE_LATITUDE_RANGE = "RULE_LATITUDE_RANGE"
RULE_LONGITUDE_RANGE = "RULE_LONGITUDE_RANGE"
RULE_MAGNITUDE_RANGE = "RULE_MAGNITUDE_RANGE"
RULE_DEPTH_RANGE = "RULE_DEPTH_RANGE"

# Plausibility Boundaries (Geophysics Standards)
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
# USGS Richter/Moment scale: microseisms can have negative magnitudes down to -2.0; > 10.0 is physically impossible
MIN_MAGNITUDE = -2.0
MAX_MAGNITUDE = 10.0
# Depths: negative down to -5.0 km for events occurring in mountainous volcanic edifices above sea level; max 1000 km
MIN_DEPTH_KM = -5.0
MAX_DEPTH_KM = 1000.0

def validate_earthquake_feature(feature: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validates a raw GeoJSON earthquake feature against strict geophysical and data integrity rules.
    Returns:
      - is_valid (bool): True if all mandatory rules pass.
      - passed_rules (List[str]): List of rule names that succeeded.
      - failed_rules (List[str]): List of rule names that failed.
    """
    passed_rules = []
    failed_rules = []
    
    # 1. Check ID
    feat_id = feature.get("id")
    if feat_id and isinstance(feat_id, str) and len(feat_id.strip()) > 0:
        passed_rules.append(RULE_ID_REQUIRED)
    else:
        failed_rules.append(RULE_ID_REQUIRED)
        
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    
    # 2. Check Time
    event_time_epoch = properties.get("time")
    if event_time_epoch is not None and isinstance(event_time_epoch, (int, float)) and event_time_epoch > 0:
        passed_rules.append(RULE_TIME_REQUIRED)
    else:
        failed_rules.append(RULE_TIME_REQUIRED)
        
    # 3. Check Coordinates existence
    coords = geometry.get("coordinates")
    coords_valid = False
    lon, lat, depth = None, None, None
    if isinstance(coords, (list, tuple)) and len(coords) >= 3:
        try:
            lon = float(coords[0])
            lat = float(coords[1])
            depth = float(coords[2])
            coords_valid = True
            passed_rules.append(RULE_COORDINATES_REQUIRED)
        except (ValueError, TypeError):
            failed_rules.append(RULE_COORDINATES_REQUIRED)
    else:
        failed_rules.append(RULE_COORDINATES_REQUIRED)
        
    # 4. Latitude range
    if coords_valid and lat is not None and MIN_LATITUDE <= lat <= MAX_LATITUDE:
        passed_rules.append(RULE_LATITUDE_RANGE)
    else:
        failed_rules.append(RULE_LATITUDE_RANGE)
        
    # 5. Longitude range
    if coords_valid and lon is not None and MIN_LONGITUDE <= lon <= MAX_LONGITUDE:
        passed_rules.append(RULE_LONGITUDE_RANGE)
    else:
        failed_rules.append(RULE_LONGITUDE_RANGE)
        
    # 6. Magnitude range
    mag = properties.get("mag")
    if mag is not None:
        try:
            mag_float = float(mag)
            if MIN_MAGNITUDE <= mag_float <= MAX_MAGNITUDE:
                passed_rules.append(RULE_MAGNITUDE_RANGE)
            else:
                failed_rules.append(RULE_MAGNITUDE_RANGE)
        except (ValueError, TypeError):
            failed_rules.append(RULE_MAGNITUDE_RANGE)
    else:
        # If magnitude is missing/null, it violates plausibility for seismic risk reporting
        failed_rules.append(RULE_MAGNITUDE_RANGE)
        
    # 7. Depth range
    if coords_valid and depth is not None and MIN_DEPTH_KM <= depth <= MAX_DEPTH_KM:
        passed_rules.append(RULE_DEPTH_RANGE)
    else:
        failed_rules.append(RULE_DEPTH_RANGE)
        
    is_valid = len(failed_rules) == 0
    return is_valid, passed_rules, failed_rules

def calculate_severity(magnitude: float) -> str:
    """
    Categorizes seismic severity for Gold layer and UI alerting:
    - CRITICAL: >= 7.0 (Major destructive earthquake)
    - HIGH: 6.0 - 6.9 (Strong earthquake)
    - MODERATE: 4.0 - 5.9 (Light to moderate earthquake)
    - LOW: < 4.0 (Minor or microseism)
    """
    if magnitude >= 7.0:
        return "CRITICAL"
    elif magnitude >= 6.0:
        return "HIGH"
    elif magnitude >= 4.0:
        return "MODERATE"
    else:
        return "LOW"
