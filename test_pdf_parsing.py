#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def test_pdf_parsing():
    """PDF parsing'i test et"""
    
    # Örnek PDF metni (tablonuzdan)
    sample_text = """
AD 2 LTFM STAR-3A                                                AIP
17 APR 25                                                     TÜRKİYE

                    ISTANBUL AIRPORT RNAV (GNSS) STAR RWY 16R/17L/18

Type    Fix identifier    Latitude        Longitude        Type    Fix identifier    Latitude        Longitude
        (Waypoint                                                  (Waypoint
        name)                                                      name)

FlyBy   AGBET           41:02:23.66N    026:53:50.73E     FlyBy   FM407           41:35:49.29N    029:06:17.85E
FlyBy   DRAMO           41:02:04.00N    026:36:40.00E     FlyBy   FM751           41:03:28.55N    027:06:59.43E
FlyBy   ENLEC           41:28:29.32N    029:05:27.20E     FlyBy   FM752           41:10:32.56N    027:14:26.61E
FlyBy   ENRAW           41:08:57.15N    028:22:54.60E     FlyBy   FM753           41:17:36.08N    027:21:55.41E
FlyBy   FM375           41:08:51.65N    028:16:17.46E     FlyBy   FM754           41:12:31.45N    027:30:18.44E
FlyBy   FM395           41:09:11.36N    028:42:45.89E     FlyBy   FM755           41:07:26.21N    027:38:40.18E
FlyBy   FM400           41:10:41.52N    029:10:33.84E     FlyBy   FM756           41:05:37.10N    027:47:36.96E
FlyBy   FM401           41:18:20.48N    029:14:28.11E     FlyBy   FM757           41:05:31.98N    027:55:33.20E
FlyBy   FM402           41:22:16.85N    029:19:31.91E     FlyBy   FM758           41:07:06.22N    028:05:56.02E
FlyBy   FM403           41:27:04.29N    029:23:04.73E     FlyBy   GUBUL           40:44:18.84N    027:18:46.36E
FlyBy   FM404           41:32:23.34N    029:24:51.88E     FlyBy   INBET           40:11:11.00N    027:16:30.00E
FlyBy   FM405           41:37:52.36N    029:24:45.60E     FlyBy   LEKMI           40:28:37.07N    027:17:41.56E
FlyBy   FM406           41:36:51.20N    029:15:31.60E     FlyBy   GAZGE           41:34:46.63N    028:57:04.36E
    """
    
    missing_waypoints = {'GAZGE', 'FM400', 'FM401', 'FM402', 'FM403', 'FM404', 'FM405', 'FM406', 'FM407'}
    
    # Test tablo parsing
    coordinates = parse_table_format(sample_text)
    print("Tablo parsing sonuçları:")
    for waypoint, coords in coordinates.items():
        if waypoint in missing_waypoints:
            print(f"✓ {waypoint}: {coords}")
    
    print(f"\nToplam bulunan: {len([w for w in coordinates.keys() if w in missing_waypoints])}")

def parse_table_format(text):
    """Tablo formatındaki koordinatları parse et"""
    coordinates = {}
    
    # Satırları böl
    lines = text.split('\n')
    
    for line in lines:
        # Tablo satırı formatını ara: FlyBy WAYPOINT LAT LON
        match = re.search(r'FlyBy\s+(\w+)\s+(\d{2,3}:\d{2}:\d{2}\.\d{2}[NS])\s+(\d{3}:\d{2}:\d{2}\.\d{2}[EW])', line)
        if match:
            waypoint, lat, lon = match.groups()
            coordinates[waypoint] = f"{lat}, {lon}"
            
    return coordinates

if __name__ == "__main__":
    test_pdf_parsing()
