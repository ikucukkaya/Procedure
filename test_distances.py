import math
from pointmerge import calculate_leg_points, calculate_point_from_bearing

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in nautical miles"""
    # Convert to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Earth radius in nautical miles
    R = 3440.065
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def test_isodistance():
    """Test if points are all at the same distance from merge point"""
    merge_lat, merge_lon = 45.0, -75.0  # Use a realistic lat/lon
    leg_distance = 10  # 10 NM
    
    # Test with different track angles and segment configurations
    print("Testing isodistance from merge point...")
    
    # Test case 1: Track 90, clockwise
    points = calculate_leg_points(
        merge_lat, merge_lon, 90, leg_distance, [2, 3, 4], clockwise=True
    )
    print("\nTrack 90° clockwise:")
    for i, p in enumerate(points):
        lat, lon = p
        distance = calculate_distance(merge_lat, merge_lon, lat, lon)
        print(f"Point {i}: lat={lat:.6f}, lon={lon:.6f}, distance from merge={distance:.6f} NM")
    
    # Test case 2: Track 180, counter-clockwise
    points = calculate_leg_points(
        merge_lat, merge_lon, 180, leg_distance, [2, 3, 4], clockwise=False
    )
    print("\nTrack 180° counter-clockwise:")
    for i, p in enumerate(points):
        lat, lon = p
        distance = calculate_distance(merge_lat, merge_lon, lat, lon)
        print(f"Point {i}: lat={lat:.6f}, lon={lon:.6f}, distance from merge={distance:.6f} NM")

if __name__ == "__main__":
    test_isodistance() 