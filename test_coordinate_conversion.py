#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def convert_coordinate_format(coord_string):
    """PDF formatındaki koordinatı waypoints.xml formatına dönüştür"""
    # 41:02:23.66N, 026:53:50.73E -> 41 02 23.66 N, 26 53 50.73 E
    try:
        # Koordinatları ayır
        parts = coord_string.split(', ')
        if len(parts) != 2:
            return None
        
        lat_part = parts[0].strip()
        lon_part = parts[1].strip()
        
        # Latitude dönüştür: 41:02:23.66N -> 41 02 23.66 N
        lat_match = re.match(r'(\d{2,3}):(\d{2}):(\d{2}\.\d{2})([NS])', lat_part)
        if lat_match:
            lat_deg, lat_min, lat_sec, lat_dir = lat_match.groups()
            formatted_lat = f"{int(lat_deg):02d} {lat_min} {lat_sec} {lat_dir}"
        else:
            return None
        
        # Longitude dönüştür: 026:53:50.73E -> 26 53 50.73 E
        lon_match = re.match(r'(\d{3}):(\d{2}):(\d{2}\.\d{2})([EW])', lon_part)
        if lon_match:
            lon_deg, lon_min, lon_sec, lon_dir = lon_match.groups()
            formatted_lon = f"{int(lon_deg):02d} {lon_min} {lon_sec} {lon_dir}"
        else:
            return None
        
        return formatted_lat, formatted_lon
        
    except Exception as e:
        print(f"Koordinat dönüştürme hatası: {e}")
        return None

def test_coordinate_conversion():
    """Koordinat dönüştürme testleri"""
    test_cases = [
        "41:02:23.66N, 026:53:50.73E",
        "41:10:41.52N, 029:10:33.84E", 
        "41:34:46.63N, 028:57:04.36E",
        "40:54:41.43N, 029:00:34.36E"
    ]
    
    print("Koordinat Dönüştürme Testleri:")
    print("=" * 50)
    
    for coord in test_cases:
        result = convert_coordinate_format(coord)
        if result:
            lat, lon = result
            print(f"Giriş:  {coord}")
            print(f"Çıkış:  {lat}, {lon}")
            print("-" * 30)
        else:
            print(f"HATA:   {coord}")
            print("-" * 30)

if __name__ == "__main__":
    test_coordinate_conversion()
