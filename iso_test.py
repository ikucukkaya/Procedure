import math
import folium
from pointmerge import calculate_leg_points, calculate_point_from_bearing, format_dms_output

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

def visualize_point_merge(merge_lat, merge_lon, leg_distance, track_angle, segment_distances, clockwise=True):
    """Visualize a point merge system with isodistance circle"""
    # Calculate leg points
    points = calculate_leg_points(
        merge_lat, merge_lon, track_angle, leg_distance, segment_distances, clockwise
    )
    
    # Create map centered at merge point
    m = folium.Map(location=[merge_lat, merge_lon], zoom_start=10)
    
    # Add merge point
    folium.Marker(
        location=[merge_lat, merge_lon],
        popup="Merge Point",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    # Add each point with distance information
    for i, point in enumerate(points):
        lat, lon = point
        dist = calculate_distance(merge_lat, merge_lon, lat, lon)
        folium.Marker(
            location=[lat, lon],
            popup=f"Point {i}: Distance from merge={dist:.3f} NM",
            icon=folium.Icon(color="blue")
        ).add_to(m)
    
    # Create sequencing leg line
    folium.PolyLine(
        locations=[[p[0], p[1]] for p in points],
        color="green",
        weight=2,
        opacity=1
    ).add_to(m)
    
    # Draw isodistance circle with radius in meters
    radius_meters = leg_distance * 1852  # Convert NM to meters
    folium.Circle(
        location=[merge_lat, merge_lon],
        radius=radius_meters,
        color="green",
        fill=False,
        weight=1,
        dash_array="5, 5"
    ).add_to(m)
    
    # Save map to HTML file
    m.save("point_merge_visualization.html")
    print(f"Map saved as 'point_merge_visualization.html'")
    print("Open this file in a browser to view the visualization.")

if __name__ == "__main__":
    # Test with a real-world coordinate
    merge_lat = 45.0
    merge_lon = -75.0
    leg_distance = 10  # NM
    track_angle = 270  # West
    segment_distances = [2, 3, 4, 5]  # NM
    
    # Check distances from merge point
    points = calculate_leg_points(
        merge_lat, merge_lon, track_angle, leg_distance, segment_distances, True
    )
    print("\nPoint distances from merge point:")
    print(f"Merge point: {merge_lat}, {merge_lon}")
    for i, p in enumerate(points):
        lat, lon = p
        distance = calculate_distance(merge_lat, merge_lon, lat, lon)
        print(f"Point {i}: lat={lat:.6f}, lon={lon:.6f}, distance={distance:.6f} NM")
    
    # Visualize
    visualize_point_merge(merge_lat, merge_lon, leg_distance, track_angle, segment_distances) 