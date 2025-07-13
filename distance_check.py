import math

def dms_to_decimal(dms_str):
    # Convert coordinate string like '410029N' or '0304944E' to decimal degrees
    is_longitude = dms_str[-1] in ['E', 'W']
    
    if is_longitude:
        # Longitude format: DDDMMSSE where DDD is degrees (3 digits)
        degrees = int(dms_str[0:3])
        minutes = int(dms_str[3:5])
        seconds = int(dms_str[5:7])
    else:
        # Latitude format: DDMMSSN where DD is degrees (2 digits)
        degrees = int(dms_str[0:2])
        minutes = int(dms_str[2:4])
        seconds = int(dms_str[4:6])
    
    direction = dms_str[-1]
    
    decimal = degrees + minutes/60 + seconds/3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

def calculate_distance(lat1, lon1, lat2, lon2):
    # Earth radius in nautical miles
    R = 3440.065
    
    # Convert to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

# Convert coordinates
o_lat = dms_to_decimal('410029N')
o_lon = dms_to_decimal('0304944E')
x_lat = dms_to_decimal('410025N')
x_lon = dms_to_decimal('0312251E')
y_lat = dms_to_decimal('403552N') 
y_lon = dms_to_decimal('0305520E')

# Calculate distances
distance_o_x = calculate_distance(o_lat, o_lon, x_lat, x_lon)
distance_o_y = calculate_distance(o_lat, o_lon, y_lat, y_lon)

# Print results
print(f'Point O: {o_lat:.5f}°N, {o_lon:.5f}°E')
print(f'Point X: {x_lat:.5f}°N, {x_lon:.5f}°E')
print(f'Point Y: {y_lat:.5f}°N, {y_lon:.5f}°E')
print(f'Distance O-X: {distance_o_x:.2f} NM')
print(f'Distance O-Y: {distance_o_y:.2f} NM')
print(f'Expected distance: 25.00 NM')
print(f'Difference O-X: {abs(distance_o_x - 25.0):.2f} NM')
print(f'Difference O-Y: {abs(distance_o_y - 25.0):.2f} NM') 