import math

def dms_to_decimal(dms_str):
    """Convert DMS coordinate string to decimal degrees"""
    # Handle North/South and East/West coordinates
    direction = dms_str[-1]  # Get N/S/E/W
    dms = dms_str[:-1]  # Remove direction letter
    
    # Split degrees, minutes, seconds
    parts = dms.split(':')
    if len(parts) != 3:
        return None
        
    try:
        degrees = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        
        decimal = degrees + minutes/60 + seconds/3600
        
        # Make negative if South or West
        if direction in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    except ValueError:
        return None

def parse_dms(dms_str):
    """Parse DMS coordinate string in format: DD MM SS.S D"""
    try:
        parts = dms_str.split()
        if len(parts) != 4:
            return None
        degrees = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        direction = parts[3]
        
        decimal = degrees + minutes/60 + seconds/3600
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    except (ValueError, IndexError):
        return None

def decimal_to_dms_str(decimal, is_latitude=True):
    """Convert decimal degrees to DMS format string"""
    # Determine direction
    direction = "N" if decimal >= 0 and is_latitude else "S" if is_latitude else "E" if decimal >= 0 else "W"
    
    # Convert to absolute value
    decimal = abs(decimal)
    
    # Extract degrees, minutes, seconds
    degrees = int(decimal)
    minutes = int((decimal - degrees) * 60)
    seconds = int(((decimal - degrees) * 60 - minutes) * 60)
    
    # Format the output
    if is_latitude:
        return f"{degrees:02d}{minutes:02d}{seconds:02d}{direction}"
    else:
        return f"{degrees:03d}{minutes:02d}{seconds:02d}{direction}"

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points in degrees"""
    # Convert to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Calculate bearing
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    bearing = math.atan2(y, x)
    
    # Convert to degrees
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing 

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance between two points in nautical miles"""
    # Earth radius in nautical miles
    EARTH_RADIUS_NM = 3440.07
    
    # Convert to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Haversine formula
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    
    a = math.sin(d_lat/2) * math.sin(d_lat/2) + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon/2) * math.sin(d_lon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = EARTH_RADIUS_NM * c
    
    return distance 

def decimal_to_dms(decimal, is_latitude=True):
    """Convert decimal degrees to DMS format"""
    # Extract degrees, minutes, seconds
    degrees = int(decimal)
    minutes = int((decimal - degrees) * 60)
    seconds = int(((decimal - degrees) * 60 - minutes) * 60)
    
    # Determine direction
    direction = "N" if decimal >= 0 and is_latitude else "S" if is_latitude else "E" if decimal >= 0 else "W"
    
    # Format the output with spaces between components
    if is_latitude:
        return f"{degrees:02d} {minutes:02d} {seconds:02d} {direction}"
    else:
        return f"{degrees:03d} {minutes:02d} {seconds:02d} {direction}"
        
def calculate_point_at_distance_and_bearing(lat1, lon1, distance_nm, bearing_deg):
    """
    Hesaplanan bir noktadan belirli bir mesafe ve yön açısında yeni nokta hesapla.
    Büyük daire mesafelerine göre doğru hesaplama yapar.
    
    Args:
        lat1, lon1: Başlangıç noktasının enlem ve boylamı (ondalık derece)
        distance_nm: Mesafe (deniz mili)
        bearing_deg: Yön açısı (derece, kuzeye göre saat yönünde)
        
    Returns:
        (lat2, lon2): Hesaplanan noktanın koordinatları (ondalık derece)
    """
    # Dünya yarıçapı (deniz mili)
    R = 3440.07  # Deniz mili cinsinden dünya yarıçapı
    
    # Derece -> radyan dönüşümü
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    bearing_rad = math.radians(bearing_deg)
    
    # Mesafeyi açısal mesafeye çevirme (radyan)
    angular_distance = distance_nm / R
    
    # Yeni noktanın koordinatlarını hesaplama (radyan)
    lat2_rad = math.asin(math.sin(lat1_rad) * math.cos(angular_distance) + 
                         math.cos(lat1_rad) * math.sin(angular_distance) * math.cos(bearing_rad))
                         
    lon2_rad = lon1_rad + math.atan2(math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1_rad),
                                    math.cos(angular_distance) - math.sin(lat1_rad) * math.sin(lat2_rad))
    
    # Radyan -> derece dönüşümü
    lat2 = math.degrees(lat2_rad)
    lon2 = math.degrees(lon2_rad)
    
    return lat2, lon2