import math
import json
import os
import csv
from PyQt5.QtWidgets import QWidget, QApplication, QFileDialog, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush
from pointmerge import calculate_point_from_bearing
from utils import calculate_distance, calculate_bearing, decimal_to_dms
from models import DataManager
from route_drawer import RouteDrawer
from trombone_popup import TrombonePopupDialog
from pointmerge_popup import PointMergePopupDialog  # Popup for point merge
from route_popup import RoutePopupDialog  # Popup for user routes
from rotation_center_dialog import RotationCenterDialog  # Döndürme merkezi seçimi için eklendi

class MapWidget(QWidget):
    """Interactive map widget for displaying airspace data"""
    
    # Define signal at class level, not in __init__
    coordinatesChanged = pyqtSignal(float, float)
    pathSelected = pyqtSignal(dict)  # New signal for path selection
    coordinatePicked = pyqtSignal(float, float, object)  # Modified to include modifiers
    routeDrawingStarted = pyqtSignal()  # Rota çizimi başladığında
    routeDrawingFinished = pyqtSignal(str, list)  # Rota ID ve noktalar
    routePointAdded = pyqtSignal(list)  # Yeni bir rota noktası eklendiğinde
    
    # Define tolerance constants for different interactions
    # Bunlar başlangıç değerleri, __init__ metodu içinde scale_factor ile çarpılıp güncellenecek
    WAYPOINT_SELECTION_TOLERANCE = 7  # pixels
    PATTERN_SELECTION_TOLERANCE = 15  # pixels
    WAYPOINT_DRAG_TOLERANCE = 10  # pixels
    
    # QColor dönüşüm yardımcısı
    def _parse_color(self, color_value, default_color=QColor(0, 128, 128)):
        """String veya QColor formatındaki renk değerini QColor nesnesine dönüştürür"""
        if isinstance(color_value, str):
            return QColor(color_value)
        elif isinstance(color_value, QColor):
            return color_value
        else:
            return default_color
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Ekran boyutunun %60'ı kadar minimum bir boyut belirle
        from PyQt5.QtWidgets import QDesktopWidget
        screen_size = QDesktopWidget().availableGeometry().size()
        min_width = int(screen_size.width())
        min_height = int(screen_size.height())
        self.setMinimumSize(min_width, min_height)
        
        # Initialize view parameters
        self.zoom = 1.2
        self.center_lat = 41.0
        self.center_lon = 29.0
        self.base_scale = 320.0  # Base scale factor for zoom level 1
        self.rotation = 0.0  # Rotation angle in degrees
        self.tilt = 0.0  # Tilt angle in degrees (0-60)
        
        # Display settings
        self.show_sids = True
        self.show_stars = True
        self.show_runways = True
        self.show_centerlines = False  # Merkez hatlarını varsayılan olarak gösterme
        self.show_north_centerline = True
        self.show_south_centerline = True
        self.centerline_length = 15.0  # Default centerline length in NM
        self.show_waypoints = False  # Waypoint görünürlük kontrolü
        self.show_segment_distances = True  # Segment mesafe etiketlerini gösterme/gizleme
        self.segment_distance_font_size = 8  # Segment mesafe etiketlerinin font boyutu (pt)
        self.trajectory_altitude_coloring = True # Add flag for trajectory coloring mode
        
        # Store drawn path extensions
        self.drawn_elements = {
            'routes': [],  # List of path extensions
            'trajectories': [], # Add list for trajectories
            'waypoints': []  # List for waypoints from coordinates.xml
        }
        
        # Waypoint display settings
        self.show_waypoints = True
        self.waypoint_color = QColor(0, 120, 255)  # Mavi renk
        self.waypoint_label_color = QColor(0, 0, 0)  # Siyah etiket
        
        # Ekran çözünürlüğüne göre ölçekleme faktörü hesapla
        from PyQt5.QtWidgets import QDesktopWidget
        screen_dpi = QDesktopWidget().physicalDpiX()  # Ekranın DPI değerini al
        # 96 DPI standart kabul edilir, ona göre ölçekleme yapalım
        self.scale_factor = max(0.75, min(1.5, screen_dpi / 96.0))  # Minimum 0.75, maksimum 1.5 ölçek
        
        self.waypoint_size = int(5 * self.scale_factor)  # Waypoint boyutu (piksel)
        self.route_id_counter = 0 # Add counter for unique route IDs
        
        # Çizgi kalınlığı ayarları - ekran çözünürlüğüne göre ölçeklenmiş
        self.normal_route_line_width = max(1, int(2 * self.scale_factor))     # Normal rota çizgi kalınlığı (px)
        self.selected_route_line_width = max(2, int(4 * self.scale_factor))   # Seçili rota çizgi kalınlığı (px)
        
        # TMA sınır ayarları
        self.show_tma_boundary = True
        self.tma_boundary_color = QColor(255, 68, 0)  # Turuncu renk
        self.tma_boundary_width = 1.5 * self.scale_factor  # Çizgi kalınlığı
        
        # LTD_P_R yasaklı saha ayarları
        self.show_restricted_areas = True
        self.restricted_area_border_color = QColor(255, 0, 0)  # Kırmızı sınır
        self.restricted_area_border_width = 1.0 * self.scale_factor  # Sınır çizgi kalınlığı
        self.restricted_area_fill_color = QColor(255, 0, 0, 40)  # Yarı saydam kırmızı dolgu
        self.restricted_area_grid_enabled = True
        self.restricted_area_grid_spacing = int(8 * self.scale_factor)  # Grid çizgileri arası piksel mesafe
        self.restricted_area_grid_color = QColor(255, 0, 0, 80)  # Yarı saydam kırmızı grid
        self.restricted_area_grid_width = 0.5 * self.scale_factor  # Grid çizgi kalınlığı
        
        # Waypoint dragging
        self.dragging_waypoint = False
        self.dragged_waypoint_index = None
        self.dragged_route_index = None
        
        # Rota taşıma modu için değişkenler
        self.route_move_mode = False
        
        # Çoklu rota seçimi için değişkenler
        self.multi_select_mode = False
        self.selected_route_indices = []  # Seçilen rotaların indeksleri
        self.route_being_moved = None  # Taşınan rotanın ID'si
        self.move_reference_point = None  # Taşıma için referans noktası (ekran koordinatları)
        self.move_start_lat_lon = None  # Taşıma başlangıcındaki harita koordinatları
        
        # Rota döndürme modu için değişkenler
        self.route_rotate_mode = False
        self.route_being_rotated = None  # Döndürülen rotanın ID'si
        self.rotate_reference_point = None  # Döndürme için referans noktası (ekran koordinatları)
        self.rotate_center_lat_lon = None  # Döndürme merkezi (coğrafi koordinatlar)
        self.rotate_start_angle = None  # Başlangıç açısı
        
        # Define a list of colors for trajectories
        self.trajectory_colors = [
            QColor(255, 0, 0),      # Red
            QColor(0, 0, 255),      # Blue
            QColor(0, 255, 0),      # Lime
            QColor(255, 165, 0),    # Orange
            QColor(0, 255, 255),    # Cyan
            QColor(255, 0, 255),    # Magenta
            QColor(255, 215, 0),    # Gold
        ]
        
        # Path selection and movement
        self.selected_path_index = None
        self.is_panning = False  # Renamed from is_moving_path
        self.is_moving_merge_point = False 
        self.is_moving_path_item = False # New flag specifically for item movement
        self.is_rotating = False 
        self.move_start_pos = None
        self.move_start_lat = 0
        self.move_start_lon = 0
        
        # Coordinate picking
        self.coordinate_picking_mode = False
        
        # Mouse tracking
        self.setMouseTracking(True)  # Enable mouse tracking for coordinate display
        self.last_mouse_pos = None
        
        # Initialize light mode colors
        self.colors = {
            'land': QColor(180, 180, 180),  # Dark gray for land
            'border': QColor(0, 0, 0),  # Daha koyu gri (daha belirgin sınırlar için)
            'procedure': QColor(0, 0, 255),  # Blue for procedures
            'waypoint': QColor(255, 0, 0),  # Red for waypoints
            'runway': QColor(0, 0, 0),  # Black for runways
            'centerline': QColor(128, 128, 128),  # Gray for centerlines
            'route': QColor(128, 0, 128),  # Purple for routes
            'background': QColor(220, 230, 240),  # Light blue for water
            
            # Çizim modları ve durumları için tutarlı renkler
            'route_drawing': QColor(0, 120, 255),    # Çizilirken mavi
            'route_default': QColor(128, 0, 128),    # Normal durumda mor
            'route_selected': QColor(255, 165, 0),   # Seçildiğinde turuncu
            'trombone_default': QColor(0, 120, 255), # Trombone normal durumda mavi
            'trombone_selected': QColor(255, 165, 0), # Trombone seçildiğinde turuncu
            'pointmerge_default': QColor(0, 120, 255), # Point merge normal durumda mavi
            'pointmerge_selected': QColor(255, 165, 0), # Point merge seçildiğinde turuncu
            'moving': QColor(0, 200, 0),             # Taşınırken yeşil
            'rotating': QColor(200, 100, 0)          # Döndürülürken turuncu-kırmızı
        }
        
        # Set initial colors
        self.land_color = self.colors['land']
        self.border_color = self.colors['border']
        self.procedure_color = self.colors['procedure']
        self.waypoint_color = self.colors['waypoint']
        self.runway_color = self.colors['runway']
        self.centerline_color = self.colors['centerline']
        self.route_color = self.colors['route']
        self.background_color = self.colors['background']
        self.country_color = self.colors['land']  # Use land color for countries
        
        # Çizim modları için renk atamalarını yap
        self.route_drawing_color = self.colors['route_drawing']
        self.route_default_color = self.colors['route_default']
        self.route_selected_color = self.colors['route_selected']
        self.moving_color = self.colors['moving']
        self.rotating_color = self.colors['rotating']
        
        # Store transformed paths
        self.country_paths = {}
        self.procedures = []
        self.runways = []
        self.selected_runways = set()  # Store selected runway IDs
        
        # Initialize geo_data as empty, will be loaded later
        self.geo_data = {"type": "FeatureCollection", "features": []} 
        self.map_bounds = None # Add to store GeoJSON bounding box

        # Rota çizimi için yeni değişkenler
        self.drawing_route = False
        self.current_route_points = []
        self.route_drawing_mode = False
        
        # Initialize route drawer
        self.route_drawer = RouteDrawer(self)
        self.route_drawer.routeDrawingStarted.connect(self.routeDrawingStarted)
        self.route_drawer.routeDrawingFinished.connect(self.routeDrawingFinished)
        self.route_drawer.routePointAdded.connect(self.routePointAdded)  # Sinyal bağlantısı
        
        # Status message
        self.status_message = ""
        
        # Keep track of last popup positions
        self.last_trombone_popup_pos = None
        self.last_pointmerge_popup_pos = None
        self.last_route_popup_pos = None
        
        # Tolerans değerlerini ekran çözünürlüğüne göre güncelle
        self.__class__.WAYPOINT_SELECTION_TOLERANCE = max(5, int(self.__class__.WAYPOINT_SELECTION_TOLERANCE * self.scale_factor))
        self.__class__.PATTERN_SELECTION_TOLERANCE = max(10, int(self.__class__.PATTERN_SELECTION_TOLERANCE * self.scale_factor))
        self.__class__.WAYPOINT_DRAG_TOLERANCE = max(7, int(self.__class__.WAYPOINT_DRAG_TOLERANCE * self.scale_factor))

    def update_status_message(self, message):
        """Update the status message and emit it to the status bar"""
        self.status_message = message
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(message)
            
    def get_scale(self):
        """Get current scale based on zoom level"""
        return self.base_scale * pow(2, self.zoom - 1)

    def compute_country_paths(self):
        """Compute QPainterPaths for countries from GeoJSON data"""
        for feature in self.geo_data['features']:
            path = QPainterPath()
            if feature['geometry']['type'] == 'Polygon':
                for ring in feature['geometry']['coordinates']:
                    self.add_ring_to_path(path, ring)
            elif feature['geometry']['type'] == 'MultiPolygon':
                for polygon in feature['geometry']['coordinates']:
                    for ring in polygon:
                        self.add_ring_to_path(path, ring)
            self.country_paths[feature['properties']['name']] = path

    def add_ring_to_path(self, path, ring):
        """Add a ring of coordinates to a QPainterPath"""
        first = True
        for coord in ring:
            point = self.geo_to_screen(coord[1], coord[0])
            if first:
                path.moveTo(point)
                first = False
            else:
                path.lineTo(point)
        path.closeSubpath()

    def geo_to_screen(self, lat, lon):
        """Convert geographic coordinates to screen coordinates using Mercator projection with rotation and tilt"""
        scale = self.get_scale()
        
        # Apply rotation transformation
        rotated_lon = (lon - self.center_lon) * math.cos(math.radians(self.rotation)) - \
                     (lat - self.center_lat) * math.sin(math.radians(self.rotation))
        rotated_lat = (lon - self.center_lon) * math.sin(math.radians(self.rotation)) + \
                     (lat - self.center_lat) * math.cos(math.radians(self.rotation))
        
        # Apply tilt transformation (simple perspective effect)
        tilt_factor = 1.0 - (self.tilt / 120.0) * (1.0 - rotated_lat / 90.0)
        
        # Convert to screen coordinates
        x = rotated_lon * scale * tilt_factor + self.width() / 2
        y = -rotated_lat * scale * tilt_factor + self.height() / 2
        
        return QPointF(x, y)

    def screen_to_geo(self, x, y):
        """Convert screen coordinates to geographic coordinates"""
        scale = self.get_scale()
        
        # Inverse of equirectangular projection
        lon = (x - self.width() / 2) / scale + self.center_lon
        lat = self.center_lat - (y - self.height() / 2) / scale
        
        return lat, lon

    def set_procedures(self, procedures):
        """Update the procedures to be displayed on the map"""
        self.procedures = procedures
        self.update()

    def set_runways(self, runways):
        """Update the runways to be displayed"""
        self.runways = runways
        self.update()

    def set_selected_runways(self, runway_ids):
        """Update which runways are selected for display"""
        self.selected_runways = set(runway_ids)
        self.update()

    def set_show_waypoints(self, show):
        """
        Waypoint görünürlüğünü ayarlar ve snap modunu buna göre günceller.
        Eğer waypoint'ler görünmüyorsa, snap modundan SNAP_WAYPOINT bitini kaldırır.
        """
        # Waypoint görünürlüğünü güncelle
        self.show_waypoints = show
        
        # Eğer route_drawer ve snap_manager varsa, waypoint görünürlüğü ve snap modunu senkronize et
        if hasattr(self, 'route_drawer') and hasattr(self.route_drawer, 'snap_manager'):
            snap_manager = self.route_drawer.snap_manager
            current_mode = snap_manager.snap_mode
            
            if not show:
                # Waypoint görünürlüğü kapalıysa, SNAP_WAYPOINT bitini kaldır
                current_mode &= ~snap_manager.SNAP_WAYPOINT
            else:
                # Waypoint görünürlüğü açıksa, daha önce SNAP_WAYPOINT aktifse tekrar aktifleştir
                # Burada görünürlük açılıyor diye otomatik olarak SNAP_WAYPOINT eklemiyoruz,
                # kullanıcının daha önce açıksa açık, kapalıysa kapalı kalmalı
                pass
                
            # Snap modunu güncelle
            snap_manager.set_snap_mode(current_mode)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zoom and rotation"""
        # Check for Ctrl + Scroll Wheel for rotation
        if event.modifiers() & Qt.ControlModifier:
            if self.selected_path_index is not None and \
               self.drawn_elements['routes'][self.selected_path_index].get('type') == 'pointmerge':
                
                # Get selected route and merge point
                route = self.drawn_elements['routes'][self.selected_path_index]
                if len(route['points']) < 2: return # Need at least merge point and one other point
                
                merge_point = route['points'][-1]
                merge_lat, merge_lon = merge_point[0], merge_point[1]
                
                # Define rotation amount (e.g., 5 degrees per step)
                rotation_delta = 5.0 if event.angleDelta().y() > 0 else -5.0
                print(f"Rotating selected Point Merge by {rotation_delta} degrees")
                
                # Rotate all points except the merge point
                new_points = []
                for i, point in enumerate(route['points']):
                    if i == len(route['points']) - 1: continue # Skip merge point itself
                    
                    lat, lon = point[0], point[1]
                    
                    # Calculate current distance and bearing from merge point
                    current_distance = calculate_distance(merge_lat, merge_lon, lat, lon)
                    current_bearing = calculate_bearing(merge_lat, merge_lon, lat, lon)
                    
                    # Calculate new bearing
                    new_bearing = (current_bearing + rotation_delta + 360) % 360
                    
                    # Calculate new point coordinates
                    new_point = calculate_point_from_bearing(merge_lat, merge_lon, current_distance, new_bearing)
                    new_points.append(new_point)
                
                # Add the merge point back at the end
                new_points.append(merge_point)
                
                # Update route data
                route['points'] = new_points
                route['segment_distances'] = self.calculate_segment_distances(new_points)
                route['segment_angles'] = self.calculate_track_angles(new_points)
                
                # Notify sidebar and update map
                self.pathSelected.emit(route)
                self.update()
                
                # Prevent default zoom behavior
                return
                
        # Default zoom behavior (if Ctrl is not pressed or no point merge selected)
        # Get the position before zoom
        old_pos = event.pos()
        old_geo = self.screen_to_geo(old_pos.x(), old_pos.y())
        
        # Update zoom level
        zoom_delta = 0.2 if event.angleDelta().y() > 0 else -0.2
        self.zoom = max(0.1, min(20.0, self.zoom + zoom_delta))
        
        # Recompute paths with new zoom level
        self.compute_country_paths()
        
        # Get the position after zoom
        new_pos = self.geo_to_screen(old_geo[0], old_geo[1])
        
        # Adjust center to keep the point under cursor fixed
        dx = old_pos.x() - new_pos.x()
        dy = old_pos.y() - new_pos.y()
        
        # Convert screen delta to geo delta
        scale = self.get_scale()
        self.center_lon += dx / scale
        self.center_lat -= dy / scale
        
        # Update the map
        self.compute_country_paths()
        self.update()

    def find_merge_point_at_click(self, point, max_distance=15):
        """Find if the click is near a merge point in a pointmerge pattern"""
        if not self.drawn_elements['routes']:
            return False, None, None
            
        click_lat, click_lon = self.screen_to_geo(point.x(), point.y())
        
        # Search through all routes
        for i, route in enumerate(self.drawn_elements['routes']):
            if route.get('type', '') == 'pointmerge' and 'points' in route:
                points = route.get('points', [])
                if len(points) > 0:
                    # Last point is the merge point in pointmerge pattern
                    merge_point = points[-1]
                    merge_point_screen = self.geo_to_screen(merge_point[0], merge_point[1])
                    
                    # Calculate distance in screen space
                    dx = merge_point_screen.x() - point.x()
                    dy = merge_point_screen.y() - point.y()
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance < max_distance:
                        return True, i, merge_point
        
        return False, None, None

    def mousePressEvent(self, event):
        """Handle mouse press events for panning, rotation, and item selection."""
        if self.route_drawer.route_drawing_mode:
            self.route_drawer.handle_mouse_press(event)
            return
            
        # Use middle mouse button for panning
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.move_start_pos = event.pos()
            self.move_start_lat, self.move_start_lon = self.screen_to_geo(event.pos().x(), event.pos().y())
            self.setCursor(Qt.ClosedHandCursor)
            self.update_status_message("Panning mode active - Drag with middle mouse button to pan")
            return
            
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            
            # First check for waypoint selection/dragging
            for route_index, route in enumerate(self.drawn_elements['routes']):
                # Rotalar içindeki tüm pointlerin taşınabilmesi için tip kontrolünü kaldırıyoruz
                # Artık ne tür olursa olsun waypoint'leri taşıyabileceğiz
                for wp_index, (lat, lon) in enumerate(route['points']):
                    screen_pos = self.geo_to_screen(lat, lon)
                    if (screen_pos - pos).manhattanLength() < self.WAYPOINT_SELECTION_TOLERANCE:
                        self.dragging_waypoint = True
                        self.dragged_waypoint_index = wp_index
                        self.dragged_route_index = route_index
                        self.setCursor(Qt.ClosedHandCursor)
                        self.update_status_message("Dragging route waypoint - Release to set new position")
                        return
            
            # If coordinate picking mode is active, handle coordinate selection
            if self.coordinate_picking_mode:
                lat, lon = self.screen_to_geo(event.pos().x(), event.pos().y())
                self.coordinatePicked.emit(lat, lon, event.modifiers())
                self.update_status_message("Coordinate selected - Click again to change")
                return                # If no waypoint was clicked, check for pattern selection
            if not self.coordinate_picking_mode and not self.route_drawing_mode:
                # find_path_at_point metodu seçilen rotanın indeksini self.selected_path_index'e atar
                if self.find_path_at_point(pos):
                    if self.selected_path_index is not None:
                        # Çoklu seçim modundaysa, seçilen rotayı listeye ekle veya çıkar
                        if self.multi_select_mode:
                            self.toggle_route_selection(self.selected_path_index)
                            selected_count = len(self.selected_route_indices)
                            self.update_status_message(f"Çoklu seçim: {selected_count} rota seçildi")
                            self.update()
                            return
                            
                        selected_route = self.drawn_elements['routes'][self.selected_path_index]
                        pattern_type = selected_route.get('type', '')
                        
                        # Tüm desenler için sadece seçim işlemi yap, popup için çift tıklama gerekecek
                        if pattern_type == 'trombone':
                            self.pathSelected.emit(selected_route)
                            self.update_status_message("Trombone selected - Double-click to open options")
                            return
                        elif pattern_type == 'pointmerge':
                            self.pathSelected.emit(selected_route)
                            self.update_status_message("Point Merge selected - Double-click to open options")
                            return
                        elif pattern_type == 'user_route':
                            self.pathSelected.emit(selected_route)
                            self.update_status_message("Route selected - Double-click to open options")
                            return
                        else:
                            self.update_status_message("Pattern selected - Orta fare düğmesi ile haritayı kaydır")
                    return
            
            # If nothing was selected, just store the position for potential panning
            self.move_start_pos = event.pos()
            self.move_start_lat, self.move_start_lon = self.screen_to_geo(event.pos().x(), event.pos().y())
            
        elif event.button() == Qt.RightButton:
            # Handle waypoint deletion - sadece user_route için
            pos = event.pos()
            for route_index, route in enumerate(self.drawn_elements['routes']):
                # Path extension'da noktaları silme özelliği olmamalı
                # Sadece user_route türündeki rotalar için nokta silmeye izin ver
                if route.get('type') == 'user_route':
                    for wp_index, (lat, lon) in enumerate(route['points']):
                        screen_pos = self.geo_to_screen(lat, lon)
                        if (screen_pos - pos).manhattanLength() < self.WAYPOINT_SELECTION_TOLERANCE:
                            # Remove the waypoint
                            del route['points'][wp_index]
                            
                            # Update segment distances and angles
                            route['segment_distances'] = self.calculate_segment_distances(route['points'])
                            route['segment_angles'] = self.calculate_track_angles(route['points'])
                            
                            # If this was the selected route, update sidebar
                            if self.selected_path_index == route_index:
                                self.pathSelected.emit(route)
                            
                            self.update()
                            self.update_status_message("Route waypoint deleted")
                            return
                        
    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning and waypoint dragging."""
        # Update coordinates display
        lat, lon = self.screen_to_geo(event.pos().x(), event.pos().y())
        self.coordinatesChanged.emit(lat, lon)
        
        if self.route_drawer.route_drawing_mode:
            self.route_drawer.handle_mouse_move(event)
        elif self.route_move_mode and self.route_being_moved is not None:
            # Rotayı taşıma işlemini gerçekleştir
            if self.move_reference_point is None:
                # İlk kez sürükleniyor, referans noktasını kaydet
                self.move_reference_point = event.pos()
                self.move_start_lat_lon = (lat, lon)
                return
                
            # Fare hareketinin oluşturduğu coğrafi farkı hesapla
            delta_x = event.pos().x() - self.move_reference_point.x()
            delta_y = event.pos().y() - self.move_reference_point.y()
            
            # Bu farkı coğrafi koordinatlara çevir
            scale = self.get_scale()
            delta_lat = -delta_y / scale  # Ekran koordinatları ters olduğu için eksi
            delta_lon = delta_x / (scale * math.cos(math.radians(self.center_lat)))
            
            # İlgili rotayı bul ve tüm noktalarını güncelle
            for route in self.drawn_elements.get('routes', []):
                if route.get('id') == self.route_being_moved:
                    # Tüm noktaları güncelle
                    new_points = []
                    for point_lat, point_lon in route['points']:
                        new_lat = point_lat + delta_lat
                        new_lon = point_lon + delta_lon
                        new_points.append((new_lat, new_lon))
                    route['points'] = new_points
                    
                    # Eğer bu bir trombone veya point merge ise, config'deki referans noktalarını da güncelle
                    if 'config' in route:
                        if route.get('type') == 'trombone':
                            # Trombone için başlangıç noktasını güncelle
                            if 'start_lat' in route['config'] and 'start_lon' in route['config']:
                                route['config']['start_lat'] += delta_lat
                                route['config']['start_lon'] += delta_lon
                        elif route.get('type') == 'pointmerge':
                            # Point Merge için merge noktasını güncelle
                            if 'merge_lat' in route['config'] and 'merge_lon' in route['config']:
                                route['config']['merge_lat'] += delta_lat
                                route['config']['merge_lon'] += delta_lon
                    
                    # Mesafeleri ve açıları güncelle
                    route['segment_distances'] = self.calculate_segment_distances(route['points'])
                    route['segment_angles'] = self.calculate_track_angles(route['points'])
                    
                    # UI'ı güncelle
                    self.pathSelected.emit(route)
                    break
            
            # Referans noktasını güncelle
            self.move_reference_point = event.pos()
            
            # Ekranı güncelle
            self.update()
        elif self.route_rotate_mode and self.route_being_rotated is not None and self.rotate_center_lat_lon is not None:
            # Rotayı döndürme işlemini gerçekleştir
            center_lat, center_lon = self.rotate_center_lat_lon
            center_screen = self.geo_to_screen(center_lat, center_lon)
            
            # İlk fare pozisyonunu kaydet
            if self.rotate_reference_point is None:
                self.rotate_reference_point = event.pos()
                # Başlangıç açısını hesapla
                dx1 = event.pos().x() - center_screen.x()
                dy1 = event.pos().y() - center_screen.y()
                self.rotate_start_angle = math.degrees(math.atan2(dy1, dx1))
                return
                
            # Yeni açıyı hesapla
            dx2 = event.pos().x() - center_screen.x()
            dy2 = event.pos().y() - center_screen.y()
            new_angle = math.degrees(math.atan2(dy2, dx2))
            
            # Açı değişimini hesapla - kullanıcı deneyimi için yönü tersine çevirelim
            delta_angle = -(new_angle - self.rotate_start_angle)
            
            # İlgili rotayı bul ve tüm noktalarını güncelle
            for route in self.drawn_elements.get('routes', []):
                if route.get('id') == self.route_being_rotated:
                    # Tüm noktaları döndür
                    new_points = []
                    for point_lat, point_lon in route['points']:
                        # Noktayı merkez etrafında döndür
                        if point_lat == center_lat and point_lon == center_lon:
                            # Bu merkez noktası, döndürmeden direkt ekle
                            new_points.append((point_lat, point_lon))
                            continue
                            
                        # Coğrafi koordinatları dönüşüm için düzlem koordinatlara çevir
                        x_diff = (point_lon - center_lon) * math.cos(math.radians(center_lat))
                        y_diff = point_lat - center_lat
                        
                        # Düzlemde döndür
                        angle_rad = math.radians(delta_angle)
                        x_new = x_diff * math.cos(angle_rad) - y_diff * math.sin(angle_rad)
                        y_new = x_diff * math.sin(angle_rad) + y_diff * math.cos(angle_rad)
                        
                        # Yeni düzlem koordinatları coğrafi koordinatlara geri çevir
                        new_lon = center_lon + x_new / math.cos(math.radians(center_lat))
                        new_lat = center_lat + y_new
                        
                        new_points.append((new_lat, new_lon))
                    
                    route['points'] = new_points
                    
                    # Mesafeleri ve açıları güncelle
                    route['segment_distances'] = self.calculate_segment_distances(route['points'])
                    route['segment_angles'] = self.calculate_track_angles(route['points'])
                    
                    # Eğer bu bir trombone ise, config'deki base_angle değerini güncelle
                    if route.get('type') == 'trombone' and 'config' in route:
                        # Mevcut base_angle değerini al
                        current_angle = route['config'].get('base_angle', 90.0)
                        # Yeni açıyı hesapla - delta_angle negatif olduğu için burada da tersine çevrilmiş olacak
                        new_base_angle = current_angle + delta_angle
                        # -180 ile 180 arasına normalize et
                        while new_base_angle > 180:
                            new_base_angle -= 360
                        while new_base_angle < -180:
                            new_base_angle += 360
                        # Config'i güncelle
                        route['config']['base_angle'] = new_base_angle
                        
                        # Trombone config'indeki runway bilgilerini de korumak için,
                        # sadece döndürmeyi güncelleyip, başlangıç noktasını değiştirmemek önemli
                        print(f"Trombone base_angle güncellendi: {new_base_angle} derece")
                    
                    # UI'ı güncelle
                    self.pathSelected.emit(route)
                    break
            
            # Referans açısını güncelle - döndürme yönünü tutarlı tutmak için aynı şekilde güncelliyoruz
            self.rotate_start_angle = new_angle
            
            # Ekranı güncelle
            self.update()
        elif self.dragging_waypoint:
            # Snap işlevi için snap_manager kontrolü
            # Eğer snap aktifse ve geçerli bir snap noktası varsa, o pozisyonu kullan
            if hasattr(self, 'route_drawer') and hasattr(self.route_drawer, 'snap_manager'):
                # Snap noktasını güncelle
                self.route_drawer.snap_manager.update_mouse_position(event.pos())
                
                if self.route_drawer.snap_manager.active_snap_point:
                    # Snap noktasını kullan
                    lat, lon = self.route_drawer.snap_manager.active_snap_point.geo_pos
                else:
                    # Normal fare pozisyonu
                    lat, lon = self.screen_to_geo(event.pos().x(), event.pos().y())
            else:
                # Snap yöneticisi yoksa normal fare pozisyonu
                lat, lon = self.screen_to_geo(event.pos().x(), event.pos().y())
            
            # Update existing route
            route = self.drawn_elements['routes'][self.dragged_route_index]
            route['points'][self.dragged_waypoint_index] = (lat, lon)
            
            # Waypoint isim güncellemesini kontrol et
            if 'waypoint_names' in route:
                self._check_and_update_waypoint_name(
                    self.dragged_route_index, 
                    self.dragged_waypoint_index, 
                    lat, lon
                )
            
            # Update segment distances and angles
            route['segment_distances'] = self.calculate_segment_distances(route['points'])
            route['segment_angles'] = self.calculate_track_angles(route['points'])
            
            # Emit pathSelected signal to update sidebar
            self.pathSelected.emit(route)
            
            self.update()
        elif self.is_panning:
            # Handle panning
            delta_x = self.move_start_pos.x() - event.pos().x()
            delta_y = self.move_start_pos.y() - event.pos().y()
            
            # Convert screen deltas to geographic deltas
            scale = self.get_scale()
            delta_lat = -delta_y / scale  # Negate delta_y for correct up-down movement
            delta_lon = delta_x / (scale * math.cos(math.radians(self.center_lat)))
            
            # Update center coordinates
            self.center_lat += delta_lat
            self.center_lon += delta_lon
            
            # Update start position for next move
            self.move_start_pos = event.pos()
            
            # Recompute paths with new center
            self.compute_country_paths()
            
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if self.route_drawer.route_drawing_mode:
            self.route_drawer.handle_mouse_release(event)
        elif self.dragging_waypoint:
            # Son pozisyonda waypoint isim kontrolü ve güncellemesi yap
            route = self.drawn_elements['routes'][self.dragged_route_index]
            if 'waypoint_names' in route:
                lat, lon = route['points'][self.dragged_waypoint_index]
                self._check_and_update_waypoint_name(
                    self.dragged_route_index, 
                    self.dragged_waypoint_index, 
                    lat, lon
                )
                # PathSelected sinyalini tekrar yayınla
                self.pathSelected.emit(route)
                
            # Sürükleme durumunu temizle
            self.dragging_waypoint = False
            self.dragged_waypoint_index = None
            self.dragged_route_index = None
            self.setCursor(Qt.ArrowCursor)
            self.update_status_message("Route waypoint position updated")
        elif self.route_move_mode:
            # Taşınan rotayı al ve trombone ise işaretle
            moved_route_id = self.route_being_moved
            moved_route = None
            for route in self.drawn_elements.get('routes', []):
                if route.get('id') == moved_route_id:
                    moved_route = route
                    # Eğer trombone veya point merge ise moved_or_rotated bayrağını ekle
                    if (route.get('type') == 'trombone' or route.get('type') == 'pointmerge') and 'config' in route:
                        route['config']['moved_or_rotated'] = True
                        print(f"{route.get('type')} taşındı. Parametre değişiklikleri kilitlendi. ID: {moved_route_id}")
                    break
            
            # Rota taşıma modunu sonlandır
            self.route_move_mode = False
            self.route_being_moved = None
            self.move_reference_point = None
            self.move_start_lat_lon = None
            self.setCursor(Qt.ArrowCursor)
            self.update_status_message("Route position updated")
        elif self.route_rotate_mode:
            # Döndürme işleminden önce rota tipini alalım
            rotated_route_type = None
            rotated_route = None
            rotated_route_id = self.route_being_rotated
            for route in self.drawn_elements.get('routes', []):
                if route.get('id') == rotated_route_id:
                    rotated_route_type = route.get('type', '')
                    rotated_route = route
                    # Eğer trombone veya point merge ise moved_or_rotated bayrağını ekle
                    if (route.get('type') == 'trombone' or route.get('type') == 'pointmerge') and 'config' in route:
                        route['config']['moved_or_rotated'] = True
                        print(f"{route.get('type')} döndürüldü. Parametre değişiklikleri kilitlendi. ID: {route.get('id')}")
                    break
                    
            # Rota döndürme modunu sonlandır
            self.route_rotate_mode = False
            self.route_being_rotated = None
            self.rotate_reference_point = None
            self.rotate_center_lat_lon = None
            self.rotate_start_angle = None
            self.setCursor(Qt.ArrowCursor)
            
            # Eğer döndürülen rota bir trombone ise, güncellenmiş konfig ile yeniden çiz
            if rotated_route_type == 'trombone' and rotated_route and 'config' in rotated_route:
                # Döndürme sonrası mevcut noktaları koruyalım, config üzerinden yeniden hesaplatmak yerine
                self.update_status_message("Trombone rotation completed")
                # NOT: Burada artık path_extension fonksiyonu çağrılmıyor, çünkü noktalar zaten doğru rotasyona sahip
            else:
                self.update_status_message("Route rotation completed")
        elif self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            self.update_status_message("")
            # Orta tuş bırakıldığında da panning modunu kapatmak için
            if event.button() == Qt.MiddleButton:
                self.is_panning = False

    def mouseDoubleClickEvent(self, event):
        """Handle double click events - open popup for routes and patterns"""
        if self.route_drawing_mode or self.coordinate_picking_mode:
            # Rota çizim modundayken veya koordinat seçim modundayken çift tık işlemini geçiş
            return
        
        pos = event.pos()
        
        # Çift tıklanan bölgede rota var mı kontrol et
        if self.find_path_at_point(pos):
            if self.selected_path_index is not None:
                selected_route = self.drawn_elements['routes'][self.selected_path_index]
                pattern_type = selected_route.get('type', '')
                
                # Popup açma işlemleri
                if pattern_type == 'user_route':
                    route_copy = selected_route.copy()
                    if route_copy:
                        self.show_route_popup(route_copy, pos)
                        self.update_status_message("Route options opened")
                        return
                elif pattern_type == 'trombone':
                    config = selected_route.get('config', {})
                    # Yüklenen çizimlerde config anahtarı eksik olabilir, bu durumda temel bir config oluştur
                    if not config:
                        print("Trombone için config bulunamadı, temel bir config oluşturuluyor.")
                        config = {
                            "pattern_type": "trombone",
                            "runway": {
                                "id": "unknown",
                                "heading": 0,
                                "lat": selected_route['points'][0][0] if selected_route.get('points') else 0,
                                "lon": selected_route['points'][0][1] if selected_route.get('points') else 0
                            }
                        }
                    config['id'] = selected_route.get('id', '')
                    self.show_trombone_popup(config, pos)
                    self.update_status_message("Trombone ayarları güncelleniyor")
                    return
                elif pattern_type == 'pointmerge':
                    config = selected_route.get('config', {})
                    # Yüklenen CSV dosyalarından config eksik olabilir, bu durumda temel bir config oluştur
                    if not config:
                        print("Point Merge için config bulunamadı, temel bir config oluşturuluyor.")
                        # Son nokta merge point olacak
                        merge_point = selected_route['points'][-1] if selected_route.get('points') and len(selected_route['points']) > 0 else (0, 0)
                        config = {
                            "pattern_type": "pointmerge",
                            "merge_lat": merge_point[0],
                            "merge_lon": merge_point[1],
                            "first_point_distance": 25.0,  # Varsayılan mesafe
                            "track_angle": 45.0,  # Varsayılan açı
                            "distance": 25.0,
                            "angle": 45.0
                        }
                    
                    # Config objesinin bir kopyasını oluştur
                    config = config.copy()
                    config['id'] = selected_route.get('id','')
                    
                    # Config ayarları
                    if 'first_point_distance' in config and 'distance' not in config:
                        config['distance'] = config['first_point_distance']
                    if 'track_angle' in config and 'angle' not in config:
                        config['angle'] = config['track_angle']
                    
                    self.show_pointmerge_popup(config, pos)
                    self.update_status_message("Point Merge ayarları güncelleniyor")
                    return

    def resizeEvent(self, event):
        """Handle widget resize events"""
        super().resizeEvent(event)
        self.compute_country_paths()
        self.update()

    def calculate_extended_centerline(self, start_lat, start_lon, end_lat, end_lon, length=15.0):
        """Calculate extended runway centerline coordinates"""
        # Calculate runway heading
        delta_lon = end_lon - start_lon
        delta_lat = end_lat - start_lat
        heading = math.atan2(delta_lon, delta_lat)
        
        # Convert nautical miles to degrees (approximately)
        nm_to_deg = 1/60  # 1 NM = 1/60 degree
        
        # Calculate points 1 NM before threshold and selected length after threshold for both ends
        # For first end (start coordinates)
        start_back_lat = start_lat - math.cos(heading) * nm_to_deg
        start_back_lon = start_lon - math.sin(heading) * nm_to_deg
        start_extended_lat = start_lat - math.cos(heading) * length * nm_to_deg
        start_extended_lon = start_lon - math.sin(heading) * length * nm_to_deg
        
        # For second end (end coordinates)
        end_back_lat = end_lat + math.cos(heading) * nm_to_deg
        end_back_lon = end_lon + math.sin(heading) * nm_to_deg
        end_extended_lat = end_lat + math.cos(heading) * length * nm_to_deg
        end_extended_lon = end_lon + math.sin(heading) * length * nm_to_deg
        
        return {
            'start': {
                'back': (start_back_lat, start_back_lon),
                'extended': (start_extended_lat, start_extended_lon)
            },
            'end': {
                'back': (end_back_lat, end_back_lon),
                'extended': (end_extended_lat, end_extended_lon)
            }
        }

    def paintEvent(self, event):
        """Paint the map and all elements"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), self.background_color)
        
        # Draw countries with visible borders
        painter.setBrush(QBrush(self.country_color))
        painter.setPen(QPen(self.border_color, 1.0))  # Daha kalın ve net sınırlar için
        for path in self.country_paths.values():
            painter.drawPath(path)
            
        # Draw TMA boundary if visible and points exist
        if self.show_tma_boundary and hasattr(self, 'data_manager') and self.data_manager.tma_boundary_points:
            # TMA sınırları için kesikli çizgi ayarla
            dash_pen = QPen(self.tma_boundary_color, self.tma_boundary_width, Qt.DashLine)
            dash_pen.setDashPattern([8, 4])  # 8px çizgi, 4px boşluk şeklinde kesikli çizgi
            painter.setPen(dash_pen)
            painter.setBrush(Qt.NoBrush)  # İçi doldurulmayacak
            
            # TMA sınır çizgisini oluştur
            tma_path = QPainterPath()
            first_point = True
            
            for lat, lon in self.data_manager.tma_boundary_points:
                screen_pos = self.geo_to_screen(lat, lon)
                
                if first_point:
                    tma_path.moveTo(screen_pos)
                    first_point = False
                else:
                    tma_path.lineTo(screen_pos)
            
            # TMA sınır çizgisini çiz
            painter.drawPath(tma_path)
            
        # Yasaklı/kısıtlı sahaları çiz (LTD_P_R)
        if self.show_restricted_areas and hasattr(self, 'data_manager') and self.data_manager.restricted_areas:
            for area in self.data_manager.restricted_areas:
                # Her bir kapalı alan için gerekli çizim ayarlarını yap
                area_path = QPainterPath()
                screen_points = []  # Ekran koordinatları
                
                # Saha noktalarını ekran koordinatlarına dönüştür
                for lat, lon in area['points']:
                    screen_pos = self.geo_to_screen(lat, lon)
                    screen_points.append(screen_pos)
                
                # Kapalı alan çizimini oluştur
                if screen_points:
                    area_path.moveTo(screen_points[0])
                    for i in range(1, len(screen_points)):
                        area_path.lineTo(screen_points[i])
                    area_path.closeSubpath()
                    
                    # Alanın içini dolgula
                    painter.setBrush(self.restricted_area_fill_color)
                    painter.setPen(QPen(self.restricted_area_border_color, self.restricted_area_border_width))
                    painter.drawPath(area_path)
                    
                    # Grid desenini çiz (kapalı alan içine sınırlı olarak)
                    if self.restricted_area_grid_enabled and len(screen_points) >= 3:
                        # Grid çizimini daha verimli hale getirmek için alanın sınırlarını belirle
                        bbox_min_x = min(p.x() for p in screen_points)
                        bbox_min_y = min(p.y() for p in screen_points)
                        bbox_max_x = max(p.x() for p in screen_points)
                        bbox_max_y = max(p.y() for p in screen_points)
                        
                        # Grid çizgileri için kalemi ayarla
                        spacing = self.restricted_area_grid_spacing
                        grid_pen = QPen(self.restricted_area_grid_color, self.restricted_area_grid_width)
                        painter.setPen(grid_pen)
                        
                        # Kapalı alanı kırpma masası olarak kullan
                        painter.save()  # Mevcut çizim durumunu kaydet
                        painter.setClipPath(area_path)  # Alan içine kırp
                        
                        # Yatay grid çizgilerini çiz
                        for y in range(int(bbox_min_y), int(bbox_max_y), spacing):
                            painter.drawLine(QPointF(bbox_min_x, y), QPointF(bbox_max_x, y))
                        
                        # Dikey grid çizgilerini çiz
                        for x in range(int(bbox_min_x), int(bbox_max_x), spacing):
                            painter.drawLine(QPointF(x, bbox_min_y), QPointF(x, bbox_max_y))
                            
                        painter.restore()  # Kırpma maskesini kaldır
        
        # Draw runways
        if self.show_runways and self.runways:
            painter.setPen(QPen(self.runway_color, 2))
            painter.setBrush(Qt.NoBrush)  # Runway'lerin içi doldurulmayacak
            
            for runway in self.runways:
                runway_id = runway.get('id')
                # Seçili runway'leri çiz
                if runway_id in self.selected_runways:
                    start_lat = runway.get('start_lat')
                    start_lon = runway.get('start_lon')
                    end_lat = runway.get('end_lat')
                    end_lon = runway.get('end_lon')
                    
                    if start_lat and start_lon and end_lat and end_lon:
                        # Sadece runway çizgisini çiz
                        start_point = self.geo_to_screen(start_lat, start_lon)
                        end_point = self.geo_to_screen(end_lat, end_lon)
                        painter.drawLine(start_point, end_point)
                        
                        # Merkez hatlarını çiz (eğer aktifse)
                        if self.show_centerlines:
                            # Runway ID'den pist uçlarını çıkar
                            try:
                                display_id_part = runway_id.split(' ', 1)[-1]
                                end1_name, end2_name = display_id_part.split('/')
                                key_end1 = f'show_{end1_name}'
                                key_end2 = f'show_{end2_name}'
                                
                                # Merkez hattı stilini ve uzunluğunu al
                                centerline_length = runway.get('centerline_length', 15.0)
                                centerline_style = runway.get('centerline_style', 'Dashed')
                                
                                # Merkez hattı çizgisi için kalemi ayarla
                                centerline_pen = QPen(self.centerline_color, 1)
                                if centerline_style == 'Dashed':
                                    centerline_pen.setStyle(Qt.DashLine)
                                elif centerline_style == 'Dotted':
                                    centerline_pen.setStyle(Qt.DotLine)
                                elif centerline_style == 'Bold Solid':
                                    centerline_pen.setWidth(2)
                                painter.setPen(centerline_pen)
                                
                                # Her iki uç için merkez hattı çizimlerini hesapla
                                centerline_points = self.calculate_extended_centerline(
                                    start_lat, start_lon, end_lat, end_lon, centerline_length)
                                
                                # Birinci ucun merkez hattını çiz (eğer gösterilmesi isteniyorsa)
                                if runway.get(key_end1, False):
                                    start_ext_point = self.geo_to_screen(
                                        centerline_points['start']['extended'][0], 
                                        centerline_points['start']['extended'][1])
                                    painter.drawLine(start_point, start_ext_point)
                                
                                # İkinci ucun merkez hattını çiz (eğer gösterilmesi isteniyorsa)
                                if runway.get(key_end2, False):
                                    end_ext_point = self.geo_to_screen(
                                        centerline_points['end']['extended'][0], 
                                        centerline_points['end']['extended'][1])
                                    painter.drawLine(end_point, end_ext_point)
                                
                                # Runway çizimini sürdürmek için varsayılan kalemi tekrar ayarla
                                painter.setPen(QPen(self.runway_color, 2))
                            except Exception as e:
                                # Runway ID ayrıştırılamadıysa hata raporla ama çizmeye devam et
                                print(f"Runway merkez hattı çizilemedi {runway_id}: {e}")
            
        # Draw procedures
        painter.setPen(QPen(self.procedure_color, 1))
        for procedure in self.procedures:
            # Procedure kontrolü: Eğer procedure bir liste değilse veya liste olsa bile boşsa, atla
            if not procedure or not isinstance(procedure, list):
                continue
                
            # İlk elemanın type bilgisi var mı kontrol et
            first_wp = procedure[0] if procedure else None
            proc_type = first_wp.get('type') if isinstance(first_wp, dict) else None
                
            # Procedure type kontrolü
            if proc_type == 'SID' and not self.show_sids:
                continue
            elif proc_type == 'STAR' and not self.show_stars:
                continue
                
            path = QPainterPath()
            first = True
            for waypoint in procedure:
                # Waypoint geçerli mi kontrol et
                if isinstance(waypoint, dict) and 'lat' in waypoint and 'lon' in waypoint:
                    point = self.geo_to_screen(waypoint['lat'], waypoint['lon'])
                    if first:
                        path.moveTo(point)
                        first = False
                    else:
                        path.lineTo(point)
            
            # Önemli: polygon kapatmamak için closeSubpath çağrılmamalı!
            painter.setBrush(Qt.NoBrush)  # Kesinlikle içini doldurmamak için
            painter.drawPath(path)
            
            # Draw waypoints
            painter.setPen(QPen(self.waypoint_color, 1))
            painter.setBrush(QBrush(self.waypoint_color))
            for waypoint in procedure:
                # Waypoint geçerli mi kontrol et
                if isinstance(waypoint, dict) and 'lat' in waypoint and 'lon' in waypoint:
                    point = self.geo_to_screen(waypoint['lat'], waypoint['lon'])
                    painter.drawEllipse(point, 2, 2)

        # Draw routes (path extensions)
        for i, route in enumerate(self.drawn_elements['routes']):
            if 'points' in route:
                # Get type-specific styling
                pattern_type = route.get('type', '')
                
                # Different styling for different pattern types
                if pattern_type == 'pointmerge':
                    # For point merge patterns
                    if i == self.selected_path_index or i in self.selected_route_indices:
                        # Taşıma modunda olan yol için farklı stil
                        if self.route_move_mode and route.get('id') == self.route_being_moved:
                            painter.setPen(QPen(self.colors['pointmerge_default'], 4, Qt.DashLine))  # Mavi, kesikli çizgi
                        # Döndürme modunda olan yol için farklı stil
                        elif self.route_rotate_mode and route.get('id') == self.route_being_rotated:
                            painter.setPen(QPen(QColor(200, 100, 0), 4, Qt.DotLine))  # Turuncu-kırmızı, noktalı çizgi
                        # Çoklu seçim modunda seçilen yol için farklı stil
                        elif self.multi_select_mode and i in self.selected_route_indices:
                            painter.setPen(QPen(QColor(255, 0, 255), self.selected_route_line_width))  # Mor renk, çoklu seçim için
                        else:
                            painter.setPen(QPen(self.route_selected_color, self.selected_route_line_width))  # Seçilmiş rota için kalınlık ve renk
                    else:
                        color = self._parse_color(route.get('color', '#008080'))  # Varsayılan türkuaz
                        painter.setPen(QPen(color, self.normal_route_line_width))  # Normal kalınlıkta rota çizgisi
                else:
                    # For trombone or other patterns
                    pen = QPen(self.route_default_color, self.normal_route_line_width)  # Normal rota kalınlığı
                    if i == self.selected_path_index or i in self.selected_route_indices:
                        pen.setWidth(self.selected_route_line_width)  # Seçili rota kalınlığı
                        # Taşıma modunda olan yol için farklı stil
                        if self.route_move_mode and route.get('id') == self.route_being_moved:
                            pen.setColor(QColor(0, 200, 0))  # Yeşil renk
                            pen.setStyle(Qt.DashLine)  # Kesikli çizgi
                        # Döndürme modunda olan yol için farklı stil
                        elif self.route_rotate_mode and route.get('id') == self.route_being_rotated:
                            pen.setColor(QColor(200, 100, 0))  # Turuncu-kırmızı renk
                            pen.setStyle(Qt.DotLine)  # Noktalı çizgi
                        # Çoklu seçim modunda seçilen yol için farklı stil
                        elif self.multi_select_mode and i in self.selected_route_indices:
                            pen.setColor(QColor(255, 0, 255))  # Mor renk, çoklu seçim için
                            pen.setWidth(3)
                        else:
                            pen.setColor(self.route_selected_color)  # Seçili rotanın rengi
                    painter.setPen(pen)
                
                # Draw route path
                path = QPainterPath()
                
                # Segment'ler için mesafe bilgisini kullan
                # Bu, hangi noktaların birleştirildiğinde çizgi çizilmemesi gerektiğini belirleyecek
                segment_distances = route.get('segment_distances', [])
                
                # Başlangıç noktası her zaman çizilir
                if route['points']:
                    first_point = route['points'][0]
                    first_screen_pos = self.geo_to_screen(first_point[0], first_point[1])
                    path.moveTo(first_screen_pos)
                    
                    # Diğer noktaları işle
                    for i in range(1, len(route['points'])):
                        point = route['points'][i]
                        prev_point = route['points'][i-1]
                        screen_pos = self.geo_to_screen(point[0], point[1])
                        
                        # Eğer önceki segmentin mesafesi -1 ise (noktalar çok yakın)
                        # yeni bir alt yol başlat
                        if i-1 < len(segment_distances) and segment_distances[i-1] == -1:
                            # Önceki nokta ile mevcut nokta arasında çizgi çizme
                            path.moveTo(screen_pos)  # Yeni bir alt yol başlat
                        else:
                            # Normal çizgi çiz
                            path.lineTo(screen_pos)
                
                # Bütün rotalar closeSubpath çağrılmadan çizilmeli
                # Burada özellikle dolguyu kapatıyoruz
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
                
                # Segment mesafelerini ve açılarını çizgilerin üzerine/altına yaz - göster/gizle seçeneğine bağlı olarak
                if self.show_segment_distances and 'segment_distances' in route and len(route['segment_distances']) > 0:
                    # Segment açıları bilgisini al (eğer mevcutsa)
                    segment_angles = route.get('segment_angles', [])
                    
                    for i in range(len(route['points']) - 1):
                        # -1 değerindeki segment mesafelerini gösterme (yakın noktalar)
                        if i < len(route['segment_distances']) and route['segment_distances'][i] == -1:
                            continue
                            
                        p1 = self.geo_to_screen(route['points'][i][0], route['points'][i][1])
                        p2 = self.geo_to_screen(route['points'][i+1][0], route['points'][i+1][1])
                        
                        # Çizginin orta noktası
                        mid_x = (p1.x() + p2.x()) / 2
                        mid_y = (p1.y() + p2.y()) / 2
                        
                        # Çizginin açısını hesapla
                        dx = p2.x() - p1.x()
                        dy = p2.y() - p1.y()
                        import math
                        line_angle = math.degrees(math.atan2(dy, dx))
                        
                        # Orijinal font ayarlarını sakla
                        old_font = painter.font()
                        # Yeni font ayarlarını uygula
                        font = painter.font()
                        font.setPointSize(self.segment_distance_font_size)  # Standart boyut (8pt)
                        font.setBold(True)     # Kalın font
                        painter.setFont(font)
                        
                        # Mesafe metni (çizginin altına)
                        distance_text = f"<{route['segment_distances'][i]:.1f}>"
                        
                        # Çizgiye dik olan yönü hesapla (90 derece ekle)
                        perpendicular_angle = math.radians(line_angle + 90)
                        offset = 10  # Çizgiden uzaklık (piksel cinsinden) - Daha yakın yerleşim
                        
                        # Mesafe metni için ters yön (çizginin diğer tarafı)
                        dist_rect = painter.fontMetrics().boundingRect(distance_text)
                        dist_offset_x = -offset * math.cos(perpendicular_angle)
                        dist_offset_y = -offset * math.sin(perpendicular_angle)
                        dist_pos_x = mid_x + dist_offset_x
                        dist_pos_y = mid_y + dist_offset_y
                        
                        # Mesafe metnini çizgiye paralel olarak çiz
                        painter.setPen(QPen(QColor(0, 0, 0), 1))
                        
                        # Painter durumunu kaydet
                        painter.save()
                        # Orta noktaya taşı, döndür ve metni çiz
                        painter.translate(dist_pos_x, dist_pos_y)
                        
                        # Metin döndürme açısını hesapla
                        rotation_angle = line_angle
                        
                        # Açı -180 ile +180 aralığında olacak şekilde normalize et
                        while rotation_angle > 180:
                            rotation_angle -= 360
                        while rotation_angle < -180:
                            rotation_angle += 360
                            
                        # Metnin her zaman okunabilir olması için açı ayarlaması:
                        # Eğer açı -90 ile 90 derece arasında değilse, metni 180 derece döndür
                        if rotation_angle < -90 or rotation_angle > 90:
                            rotation_angle -= 180
                            # -180 ile 180 aralığında kalmak için tekrar normalize et
                            if rotation_angle < -180:
                                rotation_angle += 360
                        
                        painter.rotate(rotation_angle)
                        painter.drawText(QPointF(-dist_rect.width()/2, dist_rect.height()/3), distance_text)
                        painter.restore()
                        
                        # Açı metni (çizginin üstüne) - eğer açı bilgisi mevcutsa
                        if i < len(segment_angles):
                            track_angle_text = f"{segment_angles[i]:.1f}°"
                            
                            # Açı metni için pozisyon hesapla
                            angle_rect = painter.fontMetrics().boundingRect(track_angle_text)
                            angle_offset_x = offset * math.cos(perpendicular_angle)
                            angle_offset_y = offset * math.sin(perpendicular_angle)
                            angle_pos_x = mid_x + angle_offset_x
                            angle_pos_y = mid_y + angle_offset_y
                            
                            # Painter durumunu kaydet
                            painter.save()
                            # Orta noktaya taşı, döndür ve metni çiz
                            painter.translate(angle_pos_x, angle_pos_y)
                            
                            # Metin döndürme açısını hesapla
                            rotation_angle = line_angle
                            
                            # Açı -180 ile +180 aralığında olacak şekilde normalize et
                            while rotation_angle > 180:
                                rotation_angle -= 360
                            while rotation_angle < -180:
                                rotation_angle += 360
                                
                            # Metnin her zaman okunabilir olması için açı ayarlaması:
                            # Eğer açı -90 ile 90 derece arasında değilse, metni 180 derece döndür
                            if rotation_angle < -90 or rotation_angle > 90:
                                rotation_angle -= 180
                                # -180 ile 180 aralığında kalmak için tekrar normalize et
                                if rotation_angle < -180:
                                    rotation_angle += 360
                            
                            painter.rotate(rotation_angle)
                            painter.drawText(QPointF(-angle_rect.width()/2, angle_rect.height()/3), track_angle_text)
                            painter.restore()
                        
                        # Orijinal font ayarlarını geri yükle
                        painter.setFont(old_font)

                # Draw isodistance circle for selected point merge pattern
                if pattern_type == 'pointmerge' and i == self.selected_path_index:
                    # Get merge point (last point) and one point on the arc
                    if len(route['points']) >= 2:
                        merge_point = route['points'][-1]  # Last point is merge point
                        merge_lat, merge_lon = merge_point[0], merge_point[1]
                        
                        # Create circle points in geographic coordinates
                        circle_points = []
                        leg_distance = route.get('config', {}).get('first_point_distance', 25.0)
                        num_points = 60  # Number of points to create the circle
                        
                        for angle in range(0, 360, int(360/num_points)):
                            # Calculate point at exact distance from merge point
                            point = calculate_point_from_bearing(merge_lat, merge_lon, leg_distance, angle)
                            # Convert to screen coordinates
                            screen_pos = self.geo_to_screen(point[0], point[1])
                            circle_points.append(screen_pos)
                        
                        # Draw dashed circle using path
                        painter.setBrush(Qt.NoBrush)
                        dash_pen = QPen(QColor(255, 165, 0), 1.5 * self.scale_factor, Qt.DashLine)  # Orange dashed line, thinner
                        dash_pen.setDashPattern([int(50 * self.scale_factor), int(50 * self.scale_factor)])  # Dash pattern scaled
                        painter.setPen(dash_pen)
                        
                        # Create circle path from points
                        circle_path = QPainterPath()
                        if circle_points:
                            circle_path.moveTo(circle_points[0])
                            for j in range(1, len(circle_points)):
                                circle_path.lineTo(circle_points[j])
                            circle_path.closeSubpath()
                        
                        painter.drawPath(circle_path)

                # For non-selected isodistance circle use a similar approach but with different styling
                elif pattern_type == 'pointmerge':
                    # Get merge point (last point) and one point on the arc
                    if len(route['points']) >= 2:
                        merge_point = route['points'][-1]  # Last point is merge point
                        merge_lat, merge_lon = merge_point[0], merge_point[1]
                        
                        # Create circle points in geographic coordinates
                        circle_points = []
                        leg_distance = route.get('config', {}).get('first_point_distance', 25.0)
                        num_points = 60  # Number of points to create the circle
                        
                        for angle in range(0, 360, int(360/num_points)):
                            # Calculate point at exact distance from merge point
                            point = calculate_point_from_bearing(merge_lat, merge_lon, leg_distance, angle)
                            # Convert to screen coordinates
                            screen_pos = self.geo_to_screen(point[0], point[1])
                            circle_points.append(screen_pos)
                        
                        # Draw dashed circle using path
                        painter.setBrush(Qt.NoBrush)
                        route_color = self._parse_color(route.get('color'))
                        dash_pen = QPen(route_color, 0.8, Qt.DashLine)  # Route-colored dashed line, thinner
                        dash_pen.setDashPattern([3, 5])
                        painter.setPen(dash_pen)
                        
                        # Create circle path from points
                        circle_path = QPainterPath()
                        if circle_points:
                            circle_path.moveTo(circle_points[0])
                            for j in range(1, len(circle_points)):
                                circle_path.lineTo(circle_points[j])
                            circle_path.closeSubpath()
                        
                        painter.drawPath(circle_path)
                
                # Draw waypoints
                waypoint_size = 4  # Reduced from 5 to 4
                for j, point in enumerate(route['points']):
                    screen_pos = self.geo_to_screen(point[0], point[1])
                    
                    # Special handling for merge point (last point in a point merge pattern)
                    if pattern_type == 'pointmerge' and j == len(route['points']) - 1:
                        # Get the color based on selection status
                        if self.route_move_mode and route.get('id') == self.route_being_moved:
                            # Taşıma modundaki rota için özel renk
                            fill_color = self.colors['pointmerge_default']  # Mavi
                        elif self.route_rotate_mode and route.get('id') == self.route_being_rotated:
                            # Döndürme modundaki rota için özel renk
                            fill_color = QColor(200, 100, 0)  # Turuncu-kırmızı
                            
                            # Bu nokta döndürme merkezi mi?
                            if self.rotate_center_lat_lon and self.rotate_center_lat_lon == (point[0], point[1]):
                                fill_color = QColor(255, 50, 50)  # Parlak kırmızı (merkez nokta)
                        elif i == self.selected_path_index:
                            fill_color = QColor(255, 165, 0)  # Orange for selected path
                        else:
                            fill_color = self._parse_color(route.get('color'))  # Use route's stored color
                            
                        # Draw triangle for merge point
                        painter.setBrush(QBrush(fill_color))
                        painter.setPen(QPen(QColor(0, 0, 0), 1))  # Black border
                        
                        # Create triangle points (pointing up)
                        triangle_size = waypoint_size + 3  # Reduced from +4 to +3
                        triangle = [
                            QPointF(screen_pos.x(), screen_pos.y() - triangle_size),  # Top point
                            QPointF(screen_pos.x() - triangle_size, screen_pos.y() + triangle_size/2),  # Bottom left
                            QPointF(screen_pos.x() + triangle_size, screen_pos.y() + triangle_size/2)   # Bottom right
                        ]
                        
                        # Draw the triangle
                        path = QPainterPath()
                        path.moveTo(triangle[0])
                        path.lineTo(triangle[1])
                        path.lineTo(triangle[2])
                        path.closeSubpath()
                        painter.drawPath(path)
                    else:
                        # Normal waypoints
                        if self.route_move_mode and route.get('id') == self.route_being_moved:
                            # Taşıma modundaki rota için özel renk
                            if pattern_type == 'pointmerge':
                                painter.setBrush(QBrush(self.colors['pointmerge_default']))  # Mavi
                            else:
                                painter.setBrush(QBrush(self.route_color))  # Route için normal renk
                        elif self.route_rotate_mode and route.get('id') == self.route_being_rotated:
                            # Döndürme modundaki rota için özel renk
                            painter.setBrush(QBrush(QColor(200, 100, 0)))  # Turuncu-kırmızı
                            
                            # Bu nokta döndürme merkezi mi?
                            if self.rotate_center_lat_lon and self.rotate_center_lat_lon == (point[0], point[1]):
                                painter.setBrush(QBrush(QColor(255, 50, 50)))  # Parlak kırmızı (merkez nokta)
                                # Döndürme merkezi için daha büyük waypoint boyutu
                                waypoint_size += 3
                        elif pattern_type == 'pointmerge':
                            # For point merge legs use the route's color (or orange if selected)
                            painter.setBrush(QBrush(QColor(255, 165, 0) if i == self.selected_path_index 
                                             else self._parse_color(route.get('color'))))
                        else:
                            # For other patterns use route color
                            painter.setBrush(QBrush(self.route_color))
                        
                        # Draw the waypoint
                        if self.route_move_mode and route.get('id') == self.route_being_moved:
                            # Taşıma modunda olan waypoint'ler için ince siyah kenarlık
                            painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.DashLine))
                        elif self.route_rotate_mode and route.get('id') == self.route_being_rotated:
                            # Döndürme modunda olan waypoint'ler için ince siyah kenarlık
                            if self.rotate_center_lat_lon and self.rotate_center_lat_lon == (point[0], point[1]):
                                # Merkez nokta için kalın kenarlık
                                painter.setPen(QPen(QColor(0, 0, 0), 2))
                            else:
                                # Diğer noktalar için noktalı çizgi
                                painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.DotLine))
                        else:
                            painter.setPen(Qt.NoPen)  # No border for waypoints
                        
                        painter.drawEllipse(screen_pos, waypoint_size, waypoint_size)
                        
                        # Waypoint ismini göster (özellikle user_route tipindekiler için)
                        if pattern_type == 'user_route':
                            # Waypoint ismini al (varsa stored isimden, yoksa WP{j+1} formatında oluştur)
                            if 'waypoint_names' in route and j < len(route['waypoint_names']):
                                wp_name = route['waypoint_names'][j]
                            else:
                                wp_name = f"WP{j+1}"
                                
                            # Özel font ayarları
                            save_font = painter.font()  # Geçerli fontu sakla
                            save_brush = painter.brush()  # Geçerli fırçayı sakla
                            save_pen = painter.pen()      # Geçerli kalemi sakla
                            
                            # Font özelliklerini ayarla (rota çizimindekiyle aynı olması için)
                            font = painter.font()
                            font.setPointSize(8)  # Font boyutunu küçült
                            font.setBold(True)    # Kalın font
                            painter.setFont(font)
                            
                            # Noktanın biraz üstünde ismi göster - yeni font ile ölçü al
                            text_rect = painter.fontMetrics().boundingRect(wp_name)
                            bg_rect = QRectF(screen_pos.x() - text_rect.width()/2 - 2, 
                                            screen_pos.y() - text_rect.height() - 8,
                                            text_rect.width() + 4, 
                                            text_rect.height() + 2)
                            
                            # İsmi yaz - özel font ile (arka plan olmadan direkt)
                            painter.setPen(QPen(QColor(0, 0, 0), 1))
                            painter.drawText(QPointF(screen_pos.x() - text_rect.width()/2, 
                                                   screen_pos.y() - text_rect.height() + 4), wp_name)
                            
                            # Önceki font ayarlarına geri dön
                            painter.setFont(save_font)
                            
                            # Önceki çizim ayarlarına geri dön
                            painter.setBrush(save_brush)
                            painter.setPen(save_pen)

        # Draw trajectories
        for trajectory in self.drawn_elements['trajectories']:
            if trajectory.get('points'):
                if self.trajectory_altitude_coloring:
                    # --- Altitude-based Coloring ---
                    # Find min and max altitude for color scaling
                    altitudes = [p[2] for p in trajectory['points'] if len(p) > 2]
                    if altitudes:
                        min_alt = min(altitudes)
                        max_alt = max(altitudes)
                        alt_range = max_alt - min_alt
                        
                        # Draw each segment with color based on altitude
                        for i in range(len(trajectory['points']) - 1):
                            p1 = trajectory['points'][i]
                            p2 = trajectory['points'][i + 1]
                            
                            # Calculate color based on altitude
                            if len(p1) > 2 and len(p2) > 2:
                                alt1, alt2 = p1[2], p2[2]
                                # Use average altitude for segment color
                                avg_alt = (alt1 + alt2) / 2
                                # Normalize altitude to 0-1 range
                                norm_alt = (avg_alt - min_alt) / alt_range if alt_range > 0 else 0.5
                                # Create color gradient from blue (low) to red (high)
                                r = int(255 * norm_alt)
                                b = int(255 * (1 - norm_alt))
                                color = QColor(r, 0, b)
                                
                                # Draw segment
                                painter.setPen(QPen(color, 1.5))
                                p1_screen = self.geo_to_screen(p1[0], p1[1])
                                p2_screen = self.geo_to_screen(p2[0], p2[1])
                                painter.drawLine(p1_screen, p2_screen)
                    else:
                        # --- Solid Color ---
                        base_color = trajectory.get('color', QColor(255, 0, 0)) # Use stored color or default red
                        painter.setPen(QPen(base_color, 1.5))
                        painter.setBrush(Qt.NoBrush)
                        
                        path = QPainterPath()
                        first_point = True
                        for lat, lon, alt in trajectory['points']:
                            # Draw all points, regardless of bounds for solid color
                            screen_pos = self.geo_to_screen(lat, lon)
                            if first_point:
                                path.moveTo(screen_pos)
                                first_point = False
                            else:
                                path.lineTo(screen_pos)
                        painter.drawPath(path) # Draw the whole path at once

        # Draw current route being drawn
        self.route_drawer.paint_route(painter)

        # Draw waypoints
        self.draw_waypoints(painter)

    def start_route_drawing(self):
        """Start route drawing mode"""
        self.route_drawer.start_route_drawing()
        self.update_status_message("Route drawing mode active - Sol tık: Nokta ekle, Sağ tık: Rota çizimini tamamla, Orta düğme: Haritayı kaydır")
        
    def cancel_route_drawing(self):
        """Cancel route drawing"""
        self.route_drawer.cancel_route_drawing()
        self.update_status_message("")

    def find_path_at_point(self, point):
        """Find if any path is near the clicked point and select it"""
        if not self.drawn_elements['routes']:
            return False
            
        click_lat, click_lon = self.screen_to_geo(point.x(), point.y())
        closest_path = None
        closest_index = -1
        min_distance = float('inf')
        
        # Screen-based distance threshold (in pixels)
        pixel_threshold = 15  # Increased from previous value for easier selection
        
        # Search through all routes
        for i, route in enumerate(self.drawn_elements['routes']):
            points = route.get('points', [])
            
            for j in range(len(points) - 1):
                # Get the two points forming a segment
                p1_lat, p1_lon = points[j]
                p2_lat, p2_lon = points[j + 1]
                
                # Convert to screen coordinates for more intuitive selection
                p1_screen = self.geo_to_screen(p1_lat, p1_lon)
                p2_screen = self.geo_to_screen(p2_lat, p2_lon)
                click_screen = QPointF(point)
                
                # Calculate distance from click to line segment in screen space
                distance = self.point_to_line_distance(click_screen, p1_screen, p2_screen)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_path = route
                    closest_index = i
        
        # If closest point is within threshold
        if min_distance < pixel_threshold:
            print(f"Path selected! Distance: {min_distance} pixels")
            self.selected_path_index = closest_index
            self.pathSelected.emit(closest_path)
            
            # Rota türüne göre farklı durum mesajı göster (ana fonksiyonda kullanılacak)
            pattern_type = closest_path.get('type', '')
            # Durum mesajlarını ana mousePressEvent metoduna taşıdık, 
            # çünkü trombone ve diğer türler için farklı işlemler yapacağız
            
            self.update()  # Redraw to show selection
            return True
            
        # Deselect if clicked away
        if self.selected_path_index is not None:
            self.selected_path_index = None
            self.update()
        
        return False
    
    def point_to_line_distance(self, p, p1, p2):
        """Calculate the distance from point p to line segment p1-p2 in screen space"""
        # Convert QPointF to x,y for easier math
        x, y = p.x(), p.y()
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        
        # Calculate squared length of segment
        l2 = (x2 - x1)**2 + (y2 - y1)**2
        
        # If segment is a point, just calculate distance to that point
        if l2 == 0:
            return math.sqrt((x - x1)**2 + (y - y1)**2)
            
        # Consider the line extending the segment, parameterized as p1 + t (p2 - p1)
        # Find projection of point p onto the line.
        # It falls where t = [(p-p1) . (p2-p1)] / |p2-p1|^2
        t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))
        
        # Projection falls on the segment if 0 <= t <= 1
        # Find the closest point on the segment
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        
        # Return distance from p to this closest point
        return math.sqrt((x - proj_x)**2 + (y - proj_y)**2)

    def draw_path_extension(self, config, route_id_to_update=None):
        """Draw a path extension on the map based on configuration, or update an existing one."""
        pattern_type = config.get('pattern_type', 'trombone')
        
        # --- Handle Update Case --- 
        if route_id_to_update:
            print(f"MapWidget attempting update for ID: {route_id_to_update}")
            # Find the index of the route to update
            route_index = -1
            for i, r in enumerate(self.drawn_elements['routes']):
                if r.get('id') == route_id_to_update:
                    route_index = i
                    break
            
            if route_index == -1:
                print(f"Error: Could not find route ID {route_id_to_update} to update.")
                return None
            
            # Recalculate waypoints using the NEW config
            waypoints_data = []
            if pattern_type == 'pointmerge':
                 from pointmerge import calculate_point_merge_waypoints
                 try:
                     # Var olan rotayı ve config'i al
                     existing_route = self.drawn_elements['routes'][route_index]
                     
                     if 'config' in existing_route:
                         existing_config = existing_route['config'].copy()
                         print(f"Mevcut point merge config: {existing_config}")
                         
                         # Kritik parametreleri doğrula ve güncellenenleri ekle
                         # Önce config'deki önemli yeni değerleri debugle
                         if 'first_point_distance' in config:
                             print(f"YENİ first_point_distance: {config['first_point_distance']}")
                         if 'track_angle' in config:  
                             print(f"YENİ track_angle: {config['track_angle']}")
                         if 'segments' in config:
                             print(f"YENİ segments: {config['segments']}")
                         
                         # Yeni config'den gelen güncellenmiş değerleri, tüm olası anahtarlar için kontrol et
                         # ÖNEMLİ: config'den gelen değerler tercih edilsin, yoksa existing_config'den alsın
                         
                         # Segment sayısını belirle
                         num_segments = config.get('num_segments', config.get('segments', existing_config.get('num_segments', 3)))
                         if isinstance(num_segments, list) and len(num_segments) > 0:
                             num_segments = len(num_segments)
                         elif not isinstance(num_segments, int):
                             num_segments = 3
                         
                         # Temel değerleri güncelle
                         existing_config.update({
                             'pattern_type': 'pointmerge',
                             'id': route_id_to_update,
                             'merge_lat': config.get('merge_lat', existing_config.get('merge_lat')),
                             'merge_lon': config.get('merge_lon', existing_config.get('merge_lon')),
                             'first_point_distance': config.get('first_point_distance', 
                                                      config.get('distance', existing_config.get('first_point_distance'))),
                             'distance': config.get('first_point_distance',
                                                   config.get('distance', existing_config.get('distance'))),
                             'track_angle': config.get('track_angle', 
                                                      config.get('angle', existing_config.get('track_angle'))),
                             'angle': config.get('track_angle',
                                                config.get('angle', existing_config.get('angle'))),
                             'num_segments': num_segments,
                             'preserve_current_position': config.get('preserve_current_position', False),
                         })
                         
                         # 'segments' değerini liste olarak ayarla
                         arc_width = 60.0  # Varsayılan yay genişliği (derece)
                         first_point_distance = existing_config['first_point_distance']
                         arc_length_nm = math.radians(arc_width) * first_point_distance
                         segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
                         existing_config['segments'] = [segment_distance] * num_segments
                         
                         # Güncellenmiş config'i kullan
                         config = existing_config
                     
                     # Eksik kritik alanları kontrol et
                     debug_keys = ['merge_lat', 'merge_lon', 'first_point_distance', 'track_angle']
                     missing_keys = [key for key in debug_keys if key not in config or config[key] is None]
                     
                     if missing_keys:
                         print(f"HATA: Point Merge hesaplaması için kritik alanlar eksik: {missing_keys}")
                         return None
                     
                     print(f"Point Merge hesaplaması için kullanılan son config: {config}")       
                     # Waypoint hesaplaması
                     waypoints_data = calculate_point_merge_waypoints(None, config)
                 except Exception as e:
                      print(f"Error during point merge update calculation: {e}")
                      import traceback
                      traceback.print_exc()
                      return None # Indicate failure
            elif pattern_type == 'trombone':
                 runway_approach_data = config.get('runway')  # Use updated config's runway data
                 if not runway_approach_data:
                     # Try to fallback to original route variable
                     existing_route = self.drawn_elements['routes'][route_index]
                     runway_approach_data = existing_route.get('config', {}).get('runway')
                 if not runway_approach_data:
                     print(f"Error: Runway approach data missing; cannot update trombone {route_id_to_update}")
                     return None
                 try:
                      from path_extension import calculate_trombone_waypoints
                      
                      # Runway verilerini detaylı şekilde kontrol et ve düzenle
                      if runway_approach_data:
                          # CSV'den yüklenen trombone'lar için özel kontroller
                          if 'start_lat' not in runway_approach_data and 'threshold_lat' in runway_approach_data:
                              # Threshold verilerini start olarak kullanalım
                              runway_approach_data['start_lat'] = runway_approach_data['threshold_lat']
                              runway_approach_data['start_lon'] = runway_approach_data['threshold_lon']
                              print("CSV trombone için threshold koordinatları start olarak ayarlandı")
                          
                          # Tüm gerekli koordinatların sayısal değerler olduğundan emin ol
                          for key in ['start_lat', 'start_lon', 'end_lat', 'end_lon', 'threshold_lat', 'threshold_lon']:
                              if key in runway_approach_data and runway_approach_data[key] is not None:
                                  try:
                                      runway_approach_data[key] = float(runway_approach_data[key])
                                  except (ValueError, TypeError):
                                      print(f"Hata: Geçersiz koordinat değeri: {key}={runway_approach_data[key]}")
                                      # Eksik veya geçersiz değer için varsayılan değer ata veya hata ver
                                      # Bu durum, CSV yükleme ve runway verilerinin bütünlüğü ile ilgili sorunları gösterir.
                                      # Şimdilik None bırakmak, calculate_trombone_waypoints'in varsayılanını tetikleyebilir.
                                      runway_approach_data[key] = None 
                      
                      # Detaylı debug bilgisi ekle
                      print(f"Trombone hesaplaması için kullanılan runway verileri:")
                      print(f"  ID: {runway_approach_data.get('id', 'N/A') if runway_approach_data else 'N/A'}")
                      print(f"  Start: {runway_approach_data.get('start_lat', 'N/A') if runway_approach_data else 'N/A'}, {runway_approach_data.get('start_lon', 'N/A') if runway_approach_data else 'N/A'}")
                      print(f"  End: {runway_approach_data.get('end_lat', 'N/A') if runway_approach_data else 'N/A'}, {runway_approach_data.get('end_lon', 'N/A') if runway_approach_data else 'N/A'}")
                      print(f"  Threshold: {runway_approach_data.get('threshold_lat', 'N/A') if runway_approach_data else 'N/A'}, {runway_approach_data.get('threshold_lon', 'N/A') if runway_approach_data else 'N/A'}")
                      
                      # Trombone parametreleri hakkında detaylı bilgi
                      print(f"Trombone parametreleri:")
                      print(f"  Threshold Distance: {config.get('threshold_distance', 'N/A')} NM")
                      print(f"  Base Angle: {config.get('base_angle', 'N/A')} derece")
                      print(f"  Base Distance: {config.get('base_distance', 'N/A')} NM")
                      print(f"  Extension Length: {config.get('extension_length', 'N/A')} NM")
                      
                      # calculate_trombone_waypoints fonksiyonuna runway_approach_data'nın bir kopyasını gönder
                      # Bu, fonksiyonun orijinal sözlüğü değiştirmesini engeller.
                      waypoints_data = calculate_trombone_waypoints(runway_approach_data.copy() if runway_approach_data else None, config)
                      
                      if not waypoints_data or len(waypoints_data) == 0:
                          print("Error: Trombone waypoint calculation returned empty result")
                          return None
                          
                 except Exception as e:
                      print(f"Error during trombone update calculation: {e}")
                      import traceback
                      traceback.print_exc()
                      
                      # Kritik bir hata oluştuğunda kullanıcıya bilgi ver
                      from PyQt5.QtWidgets import QMessageBox
                      QMessageBox.warning(None, "Trombone Error", 
                                        f"Failed to calculate trombone pattern: {str(e)}\n\n"
                                        "Please check the runway coordinates and parameters.")
                      return None # Indicate failure
            else:
                print(f"Error: Unknown pattern type '{pattern_type}' for update.")
                return None

            # Check calculation result and extract points
            if waypoints_data and len(waypoints_data) > 0:
                points_tuples = [(wp['lat'], wp['lon']) for wp in waypoints_data if 'lat' in wp and 'lon' in wp]
                if not points_tuples:
                    print("Error: Updated waypoints list is empty or malformed after extraction.")
                    return None
                    
                # Get existing route's color and type (shouldn't change on param update)
                existing_route = self.drawn_elements['routes'][route_index]
                pattern_color = self._parse_color(existing_route.get('color', QColor(128, 0, 128)))
                
                # Mevcut konumu korumak için flag kontrol edilsin
                preserve_position = config.get('preserve_current_position', False)
                
                # Mevcut noktaları al
                current_points = existing_route.get('points', [])
                
                # Point Merge rotaları için özel işlem:
                if pattern_type == 'pointmerge' and preserve_position and len(current_points) > 0:
                    # Mevcut merge point koordinatını koru, ancak diğer noktaları yeni açıya göre güncelle
                    merge_point = current_points[-1]  # Son nokta merge point
                    
                    print(f"Point Merge rotası güncelleniyor: Merge point konumu korunarak açılar değiştiriliyor")
                    print(f"Yeni açı: {config.get('track_angle', config.get('angle', 90.0))}")
                    # Hesaplanan noktaları kullan, böylece track_angle değişikliği etkili olur
                    # Ancak merge point'in konumunu koru
                    if len(points_tuples) > 0:
                        points_tuples[-1] = merge_point
                elif pattern_type == 'trombone' and preserve_position and len(current_points) > 0:
                    # Threshold Distance değişikliğinde özel durum gerekliydi
                    # Runway koordinatları (pist başlangıç noktası) sabit kalmalı,
                    # A noktası (threshold_distance'daki nokta) düzgün hareket etmeli
                    
                    # CSV'den yükleme durumunda veya normal güncellemede
                    # doğru koordinatların kullanılmasını sağla
                    if 'runway' in config:
                        # Runway verilerini kesinlikle koru - hesaplamalar runway'den yapılır
                        print(f"Trombone rotası güncelleniyor: Runway koordinatları korunarak waypoint'ler yeniden konumlandırılacak")
                        
                        # threshold_distance değişikliğinin doğru uygulanabilmesi için
                        # sadece runway koordinatlarını koruyoruz, noktaları değil
                        # calculate_trombone_waypoints bu koordinatları kullanarak noktaları doğru şekilde oluşturacak
                        print(f"Runway ve hesaplama temel parametreleri güncellendi: {config.get('threshold_distance')} NM")
                        
                        # Özellikle preserve_position false ise, noktaları tamamen yeniden hesaplamak istiyoruz
                        # böylece threshold_distance değişikliği A noktasını doğru şekilde etkileyecek
                elif preserve_position and len(current_points) > 0 and len(points_tuples) == len(current_points):
                    # Diğer rota tipleri için mevcut konumu tamamen koru
                    print(f"Rota pozisyonları korunuyor ({pattern_type} - ID: {route_id_to_update})")
                    # Mevcut pozisyonları kullan
                    points_tuples = current_points
                
                # Create the updated route configuration dictionary, reusing the ID
                updated_route_config = {
                    'points': points_tuples, 
                    'name': waypoints_data[0].get('name', f"{pattern_type.upper()}_UPD").split('_')[0],
                    'type': pattern_type,
                    'color': pattern_color,
                    'config': config.copy(), # Store the UPDATED config used
                    'id': route_id_to_update # Reuse the existing ID
                }
                
                # Update segment distances and angles in the config (important for sidebar display)
                updated_route_config['segment_distances'] = self.calculate_segment_distances(points_tuples)
                updated_route_config['segment_angles'] = self.calculate_track_angles(points_tuples)
                
                # Replace the old route data in the list
                self.drawn_elements['routes'][route_index] = updated_route_config
                
                self.update() # Redraw the map
                
                # Emit pathSelected signal with updated data to refresh sidebar
                # Ensure the selection index is still correct
                if self.selected_path_index == route_index:
                    self.pathSelected.emit(updated_route_config)
                
                return route_id_to_update # Return the ID on success
            else:
                print("Update waypoint calculation failed or returned empty list.")
                return None
        # --- End Handle Update Case ---
        
        # --- Original Logic for Creating New Route ---
        route_config = None
        # Choose color based on pattern type and potentially existing routes
        if pattern_type == 'pointmerge':
            pm_routes = [r for r in self.drawn_elements['routes'] if r.get('type', '') == 'pointmerge']
            if not config.get('editing_existing_route', False):
                # Tüm point merge'ler için aynı default rengi kullan
                pattern_color = self.colors['pointmerge_default']
            else:
                route_id = config.get('route_id')
                existing_route = next((r for r in self.drawn_elements['routes'] if r.get('id') == route_id), None)
                color_value = existing_route.get('color', self.colors['pointmerge_default']) if existing_route else self.colors['pointmerge_default']
                pattern_color = self._parse_color(color_value)
        else:
            pattern_color = QColor(128, 0, 128) # Purple for trombone
        
        # Create a base name
        pattern_prefix = 'POINT_MERGE' if pattern_type == 'pointmerge' else 'TROMBONE'
        route_index = len(self.drawn_elements.get('routes', [])) + 1
        name = f"{pattern_prefix}_{route_index}"

        # Calculate waypoints based on pattern type
        waypoints_data = [] # This will be list of dicts {'lat': ..., 'lon': ...}
        if pattern_type == 'pointmerge':
            from pointmerge import calculate_point_merge_waypoints
            waypoints_data = calculate_point_merge_waypoints(None, config) # Assumes returns list of dicts
        elif pattern_type == 'trombone':
            # Trombone için route_id kontrol et, güncellenecek rota ID'si varsa o rotanın trombone olduğundan emin ol
            if route_id_to_update:
                is_route_trombone = False
                for r in self.drawn_elements['routes']:
                    if r.get('id') == route_id_to_update and r.get('config', {}).get('pattern_type') == 'trombone':
                        is_route_trombone = True
                        break
                
                if not is_route_trombone:
                    print(f"Hata: Güncellenmek istenen rota ({route_id_to_update}) bir trombone değil!")
                    return None
            
            runway_approach_data = config.get('runway')
            if not runway_approach_data:
                print(f"Error: Runway approach data missing in trombone config")
                return None
            try:
                from path_extension import calculate_trombone_waypoints
                waypoints_data = calculate_trombone_waypoints(runway_approach_data.copy() if runway_approach_data else None, config) # Returns list of dicts
            except ImportError:
                 print("Error: Could not import calculate_trombone_waypoints.")
                 return None
            except Exception as e:
                 print(f"Error during trombone waypoint calculation: {e}")
                 import traceback
                 traceback.print_exc()
                 return None
        else:
             print(f"Error: Unknown pattern type '{pattern_type}' for path extension.")
             return None

        # If waypoints were successfully calculated
        if waypoints_data and len(waypoints_data) > 0:
            # --- FIX: Extract (lat, lon) tuples for storage --- 
            points_tuples = [(wp['lat'], wp['lon']) for wp in waypoints_data if 'lat' in wp and 'lon' in wp]
            
            if not points_tuples: # Check if extraction resulted in empty list
                print("Error: Calculated waypoints list is empty or malformed after extraction.")
                return None

            # Create the route configuration dictionary
            # Rota tipine göre özel ID öneki oluştur
            if pattern_type == 'trombone':
                id_prefix = "trombone_"
            elif pattern_type == 'pointmerge':
                id_prefix = "pointmerge_"
            else:
                id_prefix = "route_"  # Varsayılan user_route için
                
            route_config = {
                # Store the list of (lat, lon) tuples needed by paintEvent
                'points': points_tuples, 
                'name': waypoints_data[0].get('name', name).split('_')[0], # Use generated name prefix
                'type': pattern_type,
                'color': pattern_color,
                'config': config.copy(), # Store the original config used
                'id': f"{id_prefix}{self.route_id_counter}" # Tipe göre benzersiz ID
            }
            print(f"Yeni rota oluşturuluyor, tip: {pattern_type}, ID: {route_config['id']}")
            # Increment the counter for the next route
            self.route_id_counter += 1
            
            # Add to drawn elements and update display
            self.drawn_elements['routes'].append(route_config)
            self.update() # Redraw the map
            return route_config['id'] # Return the ID of the created route
        else:
             print("Waypoint calculation failed or returned empty list.")
             return None
        
    def calculate_segment_distances(self, points):
        """Calculate distances between consecutive waypoints in NM"""
        from utils import calculate_distance
        distances = []
        
        # Birleştirme toleransı - merge_selected_routes ile aynı değere sahip olmalı
        MERGE_TOLERANCE = 0.0001  # Yaklaşık 10-15 metre
        
        for i in range(len(points) - 1):
            lat1, lon1 = points[i]
            lat2, lon2 = points[i + 1]
            
            # Eğer iki nokta arasındaki mesafe belirlenen tolerans değerinden büyükse
            # bu iki nokta arasında bir segment olmalı
            distance = calculate_distance(lat1, lon1, lat2, lon2)
            
            # Eğer iki nokta arasındaki mesafe çok küçükse (aynı noktalar) 
            # segment mesafesini NaN veya -1 olarak işaretle
            # Bu, segment çizilmemesi gerektiğini işaret edecek
            if distance <= MERGE_TOLERANCE:
                distances.append(-1)  # -1 değeri, segment çizilmemesi gerektiğini belirtir
            else:
                distances.append(distance)
            
        return distances
        
    def calculate_track_angles(self, points):
        """Calculate true track angles between consecutive waypoints in degrees"""
        from utils import calculate_bearing
        angles = []
        
        for i in range(len(points) - 1):
            lat1, lon1 = points[i]
            lat2, lon2 = points[i + 1]
            angle = calculate_bearing(lat1, lon1, lat2, lon2)
            angles.append(angle)
            
        return angles

    def on_reset_view(self):
        """Reset view parameters to default values"""
        self.zoom = 1.0
        self.center_lat = 41.0
        self.center_lon = 29.0
        self.rotation = 0.0
        self.tilt = 0.0
        self.compute_country_paths()
        self.update()

    def set_centerline_length(self, length):
        """Set the length of extended centerlines in nautical miles"""
        self.centerline_length = float(length)
        self.update()

    def set_coordinate_picking_mode(self, enabled):
        """Enable or disable coordinate picking mode"""
        self.coordinate_picking_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
            self.update_status_message("Coordinate picking mode active - Click to set coordinates")
        else:
            self.setCursor(Qt.ArrowCursor)
            self.update_status_message("")

    def remove_drawn_route(self, route_id):
        """Remove a specific drawn route by its ID"""
        initial_length = len(self.drawn_elements.get('routes', []))
        self.drawn_elements['routes'] = [route for route in self.drawn_elements.get('routes', []) if route.get('id') != route_id]
        final_length = len(self.drawn_elements['routes', []])
        
        if final_length < initial_length:
            # Check if the removed route was the selected one
            if self.selected_path_index is not None:
                # Find the new index of the previously selected path or reset selection
                found_selected = False
                for i, route in enumerate(self.drawn_elements['routes']):
                    # Ideally, you would compare by ID if you store the ID of the selected path
                    # Here, we assume selection is based on index, so we just reset
                    pass # If selection was based on ID, we'd re-find it here
                
                # If the selected route was removed, clear the selection index
                # For simplicity now, always reset selection after removal
                self.selected_path_index = None
                
            self.update() # Redraw the map
            return True
        else:
            return False # Route with the given ID was not found 

    def load_and_compute_geojson(self, filepath):
        """Loads GeoJSON from the given path and computes country paths."""
        print(f"MapWidget attempting to load GeoJSON from: {filepath}")
        # Create DataManager instance just for loading this file
        # Or potentially pass DataManager instance if needed elsewhere
        temp_data_manager = DataManager()
        loaded_data = temp_data_manager.load_geo_data(filepath)
        
        if loaded_data:
            self.geo_data = loaded_data
            self.compute_country_paths() # Recompute paths with new data
            self.update() # Trigger redraw
            print("GeoJSON loaded and paths computed.")
            
            # Calculate bounding box
            self.calculate_map_bounds()
            
            return True
        else:
            print("Failed to load GeoJSON in MapWidget.")
            self.geo_data = {"type": "FeatureCollection", "features": []} # Reset to empty
            self.country_paths = {}
            self.map_bounds = None # Reset bounds if load failed
            self.update()
            return False 

    def calculate_map_bounds(self):
        """Calculate the geographic bounds of the loaded GeoJSON data."""
        if not self.geo_data or not self.geo_data.get('features'):
            self.map_bounds = None
            return
            
        min_lon, min_lat = 180, 90
        max_lon, max_lat = -180, -90

        def update_bounds(lon, lat):
            nonlocal min_lon, min_lat, max_lon, max_lat
            min_lon = min(min_lon, lon)
            min_lat = min(min_lat, lat)
            max_lon = max(max_lon, lon)
            max_lat = max(max_lat, lat)

        for feature in self.geo_data['features']:
            geom = feature.get('geometry')
            if not geom:
                continue
            geom_type = geom.get('type')
            coords = geom.get('coordinates')
            if not coords:
                continue

            if geom_type == 'Polygon':
                # coords is list of rings, first ring is outer boundary
                for lon, lat in coords[0]: 
                    update_bounds(lon, lat)
            elif geom_type == 'MultiPolygon':
                # coords is list of polygons
                for polygon in coords:
                    # polygon is list of rings, first ring is outer
                    for lon, lat in polygon[0]:
                        update_bounds(lon, lat)
            # Add other geometry types if needed (Point, LineString, etc.)

        if min_lon <= 180 and min_lat <= 90: # Check if any points were processed
            self.map_bounds = (min_lon, min_lat, max_lon, max_lat)
            print(f"Calculated map bounds: {self.map_bounds}")
        else:
            self.map_bounds = None # No valid points found
            print("Warning: Could not calculate valid map bounds from GeoJSON.")

    def add_trajectory(self, trajectory_id, points):
        """Add a parsed trajectory to the drawn elements, filtering points outside map bounds."""
        # Filter points based on map bounds
        filtered_points = []
        if self.map_bounds:
            min_lon, min_lat, max_lon, max_lat = self.map_bounds
            for lat, lon, alt in points:
                if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                    filtered_points.append((lat, lon, alt))
            if not filtered_points:
                print(f"Warning: Trajectory '{trajectory_id}' has no points within the current map bounds ({self.map_bounds}). Not adding.")
                return
        else:
            filtered_points = points # No bounds, use all points
            print("Warning: Map bounds not set, cannot filter trajectory points.")
        
        # Assign a color based on the number of trajectories already present
        color_index = len(self.drawn_elements['trajectories']) % len(self.trajectory_colors)
        traj_color = self.trajectory_colors[color_index]
        
        trajectory_data = {
            'id': trajectory_id,
            'points': filtered_points, # Use filtered points
            'color': traj_color,
            'type': 'trajectory'
        }
        self.drawn_elements['trajectories'].append(trajectory_data)
        print(f"Added trajectory '{trajectory_id}' with {len(filtered_points)} points (filtered from {len(points)}) and color {traj_color.name()}.")
        self.update() # Redraw the map to show the new trajectory
        
    def show_trombone_popup(self, trombone_config, screen_pos):
        """Show trombone settings popup at the given screen position"""
        
        # Trombone config'in kopya oluştur (orijinalini değiştirmemek için)
        popup_config = trombone_config.copy()
        
        # Rota taşındı veya döndürüldüyse uyarı mesajı göster
        moved_or_rotated = popup_config.get('moved_or_rotated', False)
        if moved_or_rotated:
            print(f"Uyarı: Bu trombone rotası taşındı veya döndürüldü. Parametre değişiklikleri kilitlendi.")
        
        # Popup menüyü oluştur
        popup = TrombonePopupDialog(popup_config, self)
        
        # Eğer daha önce bir konum kaydedildiyse, popup orada açılsın
        if self.last_trombone_popup_pos:
            popup.move(self.last_trombone_popup_pos)
        else:
            # Popup'ı tıklamanın yeterince uzağında göster
            pos = screen_pos
            offset_x = 30  # Sağa doğru offset
            offset_y = 30  # Aşağıya doğru offset
            popup.move(pos.x() + offset_x, pos.y() + offset_y)
        
        # Popup ekranın dışına taşmasın diye konum düzeltmesi
        screen = QApplication.desktop().availableGeometry()
        popup_rect = popup.geometry()
        
        # Sağ kenardan taştıysa
        if (popup_rect.right() > screen.right()):
            # Sağ yerine solda göster
            popup.move(pos.x() - popup_rect.width() - offset_x, popup_rect.top())
            
        # Alt kenardan taştıysa
        if (popup_rect.bottom() > screen.bottom()):
            popup.move(popup_rect.left(), screen.bottom() - popup_rect.height())
        
        # Trombone settings değiştiğinde sinyali bağla
        popup.tromboneSettingsChanged.connect(
            lambda updated_config: self._on_trombone_settings_changed(updated_config, trombone_config['id'])
        )
        
        # Trombone silme sinyalini bağla
        popup.tromboneRemoveRequested.connect(self._on_trombone_remove_requested)
        
        # Trombone CSV export sinyalini bağla
        popup.tromboneExportJsonRequested.connect(self._on_trombone_export_json)
        
        # Trombone taşıma sinyalini bağla
        popup.tromboneMoveRequested.connect(self._on_trombone_move_requested)
        
        # Trombone döndürme sinyalini bağla
        popup.tromboneRotateRequested.connect(self._on_trombone_rotate_requested)
        
        # Popup'ı göster
        popup.show()
        # İlk açılışta last position ayarla, drag sonrası kendi kaydedilsin
        if self.last_trombone_popup_pos is None:
            self.last_trombone_popup_pos = popup.pos()
    
    def _on_trombone_settings_changed(self, updated_config, route_id):
        """Handle trombone settings change from the popup"""
        # Önce ilgili rotanın trombone olduğundan emin olalım
        route_to_update = None
        route_index = -1
        
        for i, route in enumerate(self.drawn_elements['routes']):
            if route.get('id') == route_id:
                route_to_update = route
                route_index = i
                break
                
        if not route_to_update:
            print(f"Hata: Güncellenecek rota bulunamadı: {route_id}")
            return
            
        # Rotanın gerçekten bir trombone olduğunu doğrula
        pattern_type = route_to_update.get('config', {}).get('pattern_type', '')
        is_trombone = pattern_type == 'trombone'
        
        if not is_trombone:
            print(f"Hata: Seçilen rota bir trombone değil: {pattern_type}")
            return
            
        # Mevcut noktaları koru - taşınmış/döndürülmüş rotanın konumunu korumak için
        current_points = route_to_update.get('points', [])
        if not current_points or len(current_points) < 2:
            print(f"Hata: Trombone rotasında yeterli nokta yok!")
            return
            
        # Artık sıralama A->B->C olduğu için ilk nokta pist yaklaşım noktasıdır (A)
        # Son nokta extension end noktasıdır (C)
        
        # İlk ve son noktaların coğrafi konumlarını koru
        # Trombone rotası için önemli olan ilk ve son nokta
        if 'config' in route_to_update and 'runway' in route_to_update['config']:
            # Runway bilgilerini taşı
            current_runway = route_to_update['config']['runway']
            updated_config['runway'] = current_runway
            
        # Güncel config üzerine ekstra özellikler ekle
        config_copy = updated_config.copy()
        config_copy['pattern_type'] = 'trombone'
        
        # Mevcut pozisyonu korumak için bir flag ekle
        config_copy['preserve_current_position'] = True
        
        # Trombone deseninde threshold_distance değişiminde A noktası hareket etmeli,
        # ama pist eşiğinin (runway threshold) konumu sabit kalmalı
        if current_points and len(current_points) > 0:
            # Trombone için en önemli kısım, pist konumunu ve yönünü korumak
            if 'runway' in config_copy and 'runway' in route_to_update.get('config', {}):
                # Orijinal pist bilgilerini al
                original_runway = route_to_update['config']['runway']
                runway_dict = config_copy['runway']
                
                # Pist eşiğinin konum ve yönünü koru - bu değerler sabit kalmalı
                for key in ['start_lat', 'start_lon', 'end_lat', 'end_lon', 'threshold_lat', 'threshold_lon']:
                    if key in original_runway:
                        runway_dict[key] = original_runway[key]
                
                print(f"Trombone güncelleniyor: Pist eşiğinin konumu sabit tutuldu")
                print(f"  Threshold Distance değişiminde A noktasının hareketi sağlanıyor")
                
                # Threshold distance değişikliğinin özel durumu
                if 'threshold_distance' in config_copy and 'threshold_distance' in route_to_update.get('config', {}):
                    old_value = route_to_update['config']['threshold_distance']
                    new_value = config_copy['threshold_distance']
                    if old_value != new_value:
                        print(f"  Threshold Distance değişti: {old_value}→{new_value} NM")
                        # Threshold distance değiştiğinde pozisyon korumaması gerektiğini belirle
                        # Bu A noktasının hesaplamaya göre doğru konumlanmasını sağlar
                        config_copy['preserve_current_position'] = False
                        
                        # CSV'den import edilen trombonlarda özel işlem
                        # CSV'den yüklenen desenlerde de threshold_distance değişikliği A noktasını etkilemeli
                        if route_to_update.get('config', {}).get('is_csv_imported', False):
                            print("  CSV'den yüklenmiş trombone için özel işlem uygulanıyor")
                            # CSV'den yüklenen desenler için pozisyon koruma özelliğini tamamen devre dışı bırak
                            config_copy['is_csv_imported'] = True  # Bu bayrağı koru
        
        # Trombone ayarlarını güncelle
        self.draw_path_extension(config_copy, route_id_to_update=route_id)
        
        # Güncellenen rotayı seçili duruma getir
        self.selected_path_index = route_index
        self.pathSelected.emit(route_to_update)
        
        # Ekranı güncelle
        self.update()
    
    def _on_trombone_remove_requested(self, route_id):
        """Handle trombone remove request from the popup"""
        # Belirtilen ID'ye sahip rotayı bul ve sil
        routes = self.drawn_elements['routes']
        for i, route in enumerate(routes):
            if route.get('id') == route_id:
                del routes[i]
                self.update_status_message(f"Trombone {route_id} silindi")
                # Haritayı güncelle
                self.update()
                break
    
    def _on_trombone_save_requested(self, config):
        """Handle trombone save request from the popup"""
        # Şu an için sadece güncelleme yapıyoruz
        if 'id' in config:
            self._on_trombone_settings_changed(config, config['id'])
            self.update_status_message(f"Trombone {config['id']} kaydedildi")
            # Gerçek bir kaydetme işlemi için dosya operasyonları eklenebilir

    def _on_trombone_export_csv(self, route_id):
        """Handle export CSV request from trombone popup"""
        # Find route by ID
        route = next((r for r in self.drawn_elements.get('routes', []) if r.get('id') == route_id), None)
        if not route:
            QMessageBox.warning(self, "No Data", "No route data found to export.")
            return
        route_name = route.get('name', f"route_{route_id}")
        default_filename = f"{route_name}.csv"

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Route Data", default_filename,
                                                  "CSV Files (*.csv);;All Files (*)", options=options)
        if filePath:
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write Route Info
                    writer.writerow(["Route Name:", route.get('name', '')])
                    writer.writerow(["Route Type:", route.get('type', '')])
                    
                    # Rota tipine göre özel yapılandırma bilgilerini kaydet
                    if route.get('type') == 'pointmerge' and 'config' in route:
                        config = route.get('config', {})
                        writer.writerow(["Point Merge Configuration:", ""])
                        first_point_distance = config.get('first_point_distance', config.get('distance', 25.0))
                        writer.writerow(["First Point Distance (NM):", f"{first_point_distance:.2f}"])
                        track_angle = config.get('track_angle', config.get('angle', 90.0))
                        writer.writerow(["Track Angle (°):", f"{track_angle:.2f}"])
                        num_segments = config.get('num_segments', 3)
                        writer.writerow(["Number of Segments:", f"{num_segments}"])
                        # Rota taşındı/döndürüldü mü?
                        moved_or_rotated = config.get('moved_or_rotated', False)
                        writer.writerow(["Moved or Rotated:", "Yes" if moved_or_rotated else "No"])
                    
                    # Trombone özel bilgileri de kaydet
                    elif route.get('type') == 'trombone' and 'config' in route:
                        config = route.get('config', {})
                        writer.writerow(["Trombone Configuration:", ""])
                        # Rota taşındı/döndürüldü mü?
                        moved_or_rotated = config.get('moved_or_rotated', False)
                        writer.writerow(["Moved or Rotated:", "Yes" if moved_or_rotated else "No"])
                        
                    # Toplam mesafeyi ekle
                    if 'segment_distances' in route:
                        total_distance = sum(route['segment_distances'])
                        writer.writerow(["Total Distance (NM):", f"{total_distance:.2f}"])
                    writer.writerow([])
                    
                    # Write Waypoints
                    writer.writerow(["Waypoints"])
                    writer.writerow(["Wpt", "Lat (DMS)", "Lon (DMS)", "Lat (Dec)", "Lon (Dec)"])
                    points = route.get('points', [])
                    waypoint_names = route.get('waypoint_names', [])
                    if len(waypoint_names) != len(points):
                        waypoint_names = [f"WP{i+1}" for i in range(len(points))]
                    for name, (lat, lon) in zip(waypoint_names, points):
                        lat_dms = decimal_to_dms(lat, is_latitude=True)
                        lon_dms = decimal_to_dms(lon, is_latitude=False)
                        writer.writerow([name, lat_dms, lon_dms, f"{lat:.6f}", f"{lon:.6f}"])
                self.update_status_message(f"Route {route_name} exported to CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save CSV file: {e}")
        else:
            print("Export CSV cancelled.")

    def _on_trombone_export_json(self, route_id):
        """Handle export JSON request from trombone popup"""
        # Find route by ID
        route = next((r for r in self.drawn_elements.get('routes', []) if r.get('id') == route_id), None)
        if not route:
            QMessageBox.warning(self, "No Data", "No route data found to export.")
            return
        route_name = route.get('name', f"route_{route_id}")
        
        # Trombone için özel file ismi formatı oluştur
        if route.get('type') == 'trombone':
            # TLTBA23A90B5E3 formatını Trombone_LTBA23A90B5E3 formatına dönüştür
            if route_name.startswith('T') and len(route_name) > 1:
                default_filename = f"Trombone_{route_name[1:]}.json"  # T harfini çıkarıp Trombone_ ekle
            else:
                # Eğer beklenen format değilse, yine de Trombone_ önekini kullan
                default_filename = f"Trombone_{route_name}.json"
        else:
            default_filename = f"{route_name}.json"

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Route Data", default_filename,
                                                 "JSON Files (*.json);;All Files (*)", options=options)
        if filePath:
            try:
                # JSON formatında tek bir rotayı kaydet
                export_data = {
                    'routes': [route]
                }
                
                from json_utils import json_dumps
                with open(filePath, 'w', encoding='utf-8') as f:
                    json_data = json_dumps(export_data, indent=4)
                    f.write(json_data)
                
                self.update_status_message(f"Route {route_name} exported to JSON.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save JSON file: {e}")
        else:
            print("Export JSON cancelled.")

    def show_pointmerge_popup(self, pm_config, screen_pos):
        """Show point merge settings popup at the given screen position"""
        popup = PointMergePopupDialog(pm_config, self)
        # Position logic: reuse last or offset
        if self.last_pointmerge_popup_pos:
            popup.move(self.last_pointmerge_popup_pos)
        else:
            offset_x, offset_y = 30, 30
            popup.move(screen_pos.x() + offset_x, screen_pos.y() + offset_y)
        # Boundary checks
        screen = QApplication.desktop().availableGeometry()
        rect = popup.geometry()
        if rect.right() > screen.right():
            popup.move(rect.left() - rect.width(), rect.top())
        if rect.bottom() > screen.bottom():
            popup.move(rect.left(), screen.bottom() - rect.height())
        # Connect signals
        popup.pointMergeSettingsChanged.connect(
            lambda cfg: self._on_pointmerge_settings_changed(cfg, pm_config['id'])
        )
        popup.pointMergeRemoveRequested.connect(self._on_pointmerge_remove_requested)
        popup.pointMergeExportJsonRequested.connect(self._on_pointmerge_export_json)
        popup.pointMergeMoveRequested.connect(self._on_pointmerge_move_requested)
        popup.pointMergeRotateRequested.connect(self._on_pointmerge_rotate_requested)
        # Show and record pos
        popup.show()
        if self.last_pointmerge_popup_pos is None:
            self.last_pointmerge_popup_pos = popup.pos()
    
    def _on_pointmerge_settings_changed(self, cfg, route_id):
        """Handle pointmerge settings change"""
        print(f"Point Merge güncelleniyor, ID: {route_id}")
        
        # Öncelikle mevcut rotayı bul
        current_route = None
        route_index = -1
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                current_route = route
                route_index = i
                break
        
        # Eğer mevcut rota bulunamadıysa, hata mesajı göster
        if not current_route:
            print(f"Hata: {route_id} ID'li Point Merge bulunamadı!")
            return
            
        # Mevcut noktaları koru - taşınmış/döndürülmüş rotanın konumunu korumak için
        current_points = current_route.get('points', [])
        if not current_points or len(current_points) < 2:
            print(f"Hata: Point Merge rotasında yeterli nokta yok!")
            return
            
        # Mevcut merge point (son nokta)
        current_merge_point = current_points[-1]
        
        # Tüm gerekli parametrelerin olduğundan emin ol
        if 'config' in current_route:
            original_cfg = current_route['config']
            print(f"Mevcut Point Merge config: {original_cfg}")
            
            # Yeni parametre değerleri için orijinal config'i bir temel olarak kopyala 
            updated_cfg = original_cfg.copy()
            
            # Segment sayısını belirle
            num_segments = cfg.get('num_segments', cfg.get('segments', original_cfg.get('num_segments', 3)))
            if isinstance(num_segments, list) and len(num_segments) > 0:
                num_segments = len(num_segments)
            elif not isinstance(num_segments, int):
                num_segments = 3
            
            # Kullanıcının değiştirdiği yeni değerleri ekle
            updated_cfg.update({
                'pattern_type': 'pointmerge',
                # Bu değerleri her iki isimle de kaydet
                'first_point_distance': cfg.get('first_point_distance', cfg.get('distance', original_cfg.get('first_point_distance', 15.0))),
                'track_angle': cfg.get('track_angle', cfg.get('angle', original_cfg.get('track_angle', 90.0))), 
                'num_segments': num_segments,
                # ÖNEMLİ: merge point koordinatlarını mevcut güncel konumdan al
                'merge_lat': current_merge_point[0],
                'merge_lon': current_merge_point[1],
                'id': route_id
            })
            
            # 'segments' değerini liste olarak ayarla
            # Segment uzunluklarını oluştur
            arc_width = 60.0  # Varsayılan yay genişliği (derece)
            first_point_distance = updated_cfg['first_point_distance']
            arc_length_nm = math.radians(arc_width) * first_point_distance
            segment_distance = arc_length_nm / num_segments if num_segments > 0 else arc_length_nm
            updated_cfg['segments'] = [segment_distance] * num_segments
            
            # İlgili değerlerin uyumluluğu için distance ve angle değerlerini de güncelle
            updated_cfg['distance'] = updated_cfg['first_point_distance']
            updated_cfg['angle'] = updated_cfg['track_angle']
            
            # ÖNEMLİ: Mevcut konumu korumak için bir flag ekleyelim
            updated_cfg['preserve_current_position'] = True
            
        else:
            # config eksikse, sadece yeni cfg'yi kullan
            updated_cfg = cfg
            # Mevcut merge point konumunu ekle
            updated_cfg['merge_lat'] = current_merge_point[0]
            updated_cfg['merge_lon'] = current_merge_point[1]
            updated_cfg['preserve_current_position'] = True
        
        # Kritik alan kontrolü
        critical_fields = ['merge_lat', 'merge_lon', 'first_point_distance', 'track_angle']
        missing_fields = [field for field in critical_fields if field not in updated_cfg]
        
        if missing_fields:
            print(f"UYARI: Point Merge güncellemesi için kritik alanlar eksik: {missing_fields}")
            return
            
        print(f"Point Merge için kullanılacak güncellenmiş config: {updated_cfg}")
        
        # Güncellenen point merge rotasını çiz
        self.draw_path_extension(updated_cfg, route_id_to_update=route_id)
        
        # Güncellenen rotayı seçili duruma getir
        for i, route in enumerate(self.drawn_elements['routes']):
            if route.get('id') == route_id:
                self.selected_path_index = i
                self.pathSelected.emit(route)
                break
                
        # Durum mesajını güncelle ve haritayı yeniden çiz
        self.update_status_message(f"Point Merge {route_id} güncellendi")
        self.update()
    
    def _on_pointmerge_remove_requested(self, route_id):
        """Handle pointmerge removal"""
        routes = self.drawn_elements.get('routes', [])
        for i, r in enumerate(routes):
            if r.get('id') == route_id:
                del routes[i]
                self.update_status_message(f"Point Merge {route_id} silindi")
                self.update()
                break
    
    def _on_pointmerge_export_json(self, route_id):
        """Export pointmerge route to JSON"""
        # Find route by ID
        route = next((r for r in self.drawn_elements.get('routes', []) if r.get('id') == route_id), None)
        if not route:
            QMessageBox.warning(self, "No Data", "No route data found to export.")
            return
            
        # Point Merge için özel dosya adı oluştur
        route_index = route_id.split('_')[-1] if '_' in route_id else '1'  # ID'den indeks al
        default_filename = f"Point_Merge_{route_index}.json"

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Route Data", default_filename,
                                                 "JSON Files (*.json);;All Files (*)", options=options)
        if filePath:
            try:
                # JSON formatında tek bir rotayı kaydet
                export_data = {
                    'routes': [route]
                }
                
                from json_utils import json_dumps
                with open(filePath, 'w', encoding='utf-8') as f:
                    json_data = json_dumps(export_data, indent=4)
                    f.write(json_data)
                
                self.update_status_message(f"Point Merge route exported to JSON.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save JSON file: {e}")
        else:
            print("Export JSON cancelled.")

    def show_route_popup(self, route_config, screen_pos):
        """Show user route settings popup at the given screen position"""
        popup = RoutePopupDialog(route_config, self)
        
        # Position logic: reuse last or offset
        if self.last_route_popup_pos:
            popup.move(self.last_route_popup_pos)
        else:
            # Popup'ı tıklamanın yeterince uzağında göster
            pos = screen_pos
            offset_x = 30  # Sağa doğru offset
            offset_y = 30  # Aşağıya doğru offset
            popup.move(pos.x() + offset_x, pos.y() + offset_y)
        
        # Popup ekranın dışına taşmasın diye konum düzeltmesi
        screen = QApplication.desktop().availableGeometry()
        popup_rect = popup.geometry()
        
        # Sağ kenardan taştıysa
        if (popup_rect.right() > screen.right()):
            # Sağ yerine solda göster
            popup.move(pos.x() - popup_rect.width() - offset_x, popup_rect.top())
            
        # Alt kenardan taştıysa
        if (popup_rect.bottom() > screen.bottom()):
            popup.move(popup_rect.left(), screen.bottom() - popup_rect.height())
        
        # Route silme sinyalini bağla
        popup.routeRemoveRequested.connect(self._on_route_remove_requested)
        
        # Route JSON export sinyalini bağla
        popup.routeExportJsonRequested.connect(self._on_route_export_json)
        
        # Route taşıma sinyalini bağla
        popup.routeMoveRequested.connect(self._on_route_move_requested)
        
        # Route döndürme sinyalini bağla
        popup.routeRotateRequested.connect(self._on_route_rotate_requested)
        
        # Popup'ı göster
        popup.show()
        
        # İlk açılışta last position ayarla, drag sonrası kendi kaydedilsin
        if self.last_route_popup_pos is None:
            self.last_route_popup_pos = popup.pos()
    
    def _on_route_remove_requested(self, route_id):
        """Handle route remove request from the popup"""
        # Belirtilen ID'ye sahip rotayı bul ve sil
        routes = self.drawn_elements['routes']
        for i, route in enumerate(routes):
            if route.get('id') == route_id:
                del routes[i]
                self.update_status_message(f"Route {route_id} silindi")
                # Haritayı güncelle
                self.update()
                break
    
    def _on_route_export_json(self, route_id):
        """Handle route export to JSON request from the popup"""
        # Belirtilen ID'ye sahip rotayı bul
        route_data = None
        route_name = "Route"
        route_index = "1"
        
        for route in self.drawn_elements['routes']:
            if route.get('id') == route_id:
                route_data = route
                # ID'den indeks numarasını al
                if '_' in route_id:
                    route_index = route_id.split('_')[-1]
                # Özel olarak formatlanmış dosya adı oluştur
                route_name = f"Route_{route_index}"
                break
                
        if not route_data or not route_data.get('points'):
            QMessageBox.warning(self, "Export Error", "No valid route data found.")
            return
            
        # JSON dosyası için dosya seçici göster
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # Trombone ve Point Merge ile aynı dialog stilini kullan
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Route Data", 
            f"{route_name}.json",
            "JSON Files (*.json);;All Files (*)", 
            options=options
        )
        
        if filename:
            try:
                # JSON formatında tek bir rotayı kaydet
                export_data = {
                    'routes': [route_data]
                }
                
                from json_utils import json_dumps
                with open(filename, 'w', encoding='utf-8') as f:
                    json_data = json_dumps(export_data, indent=4)
                    f.write(json_data)
                    
                self.update_status_message(f"Route {route_name} exported to JSON.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save JSON file: {e}")
        else:
            print("Export JSON cancelled.")

    def _on_route_export_csv(self, route_id):
        """Handle route export to CSV request from the popup"""
        # Bu metod artık kullanılmıyor, JSON export kullanılıyor
        # Geriye dönük uyumluluk için bırakıldı
        print("CSV export replaced with JSON export")

    def _on_route_move_requested(self, route_id):
        """User Route taşıma modunu etkinleştir"""
        self._start_route_move_mode(route_id)
    
    def _on_trombone_move_requested(self, route_id):
        """Trombone taşıma modunu etkinleştir"""
        # ID formatı kontrolü ekle
        if not route_id.startswith("trombone_") and not "_" in route_id:
            print(f"UYARI: {route_id} ID'si bir trombone formatında değil. 'trombone_' önekiyle başlaması beklenir.")
            
        # Route ID'nin gerçekten bir trombone'a ait olduğunu kontrol et
        route_found = False
        for route in self.drawn_elements.get('routes', []):
            if route.get('id') == route_id:
                route_type = route.get('type', route.get('config', {}).get('pattern_type', ''))
                if route_type == 'trombone':
                    route_found = True
                    print(f"Geçerli trombone bulundu, ID: {route_id}, taşıma modu başlatılıyor")
                    self._start_route_move_mode(route_id)
                else:
                    print(f"HATA: {route_id} ID'li rota bir trombone değil! Tip: {route_type}")
                break
                
        if not route_found:
            print(f"HATA: {route_id} ID'li trombone bulunamadı")
    
    def _on_pointmerge_move_requested(self, route_id):
        """Point Merge taşıma modunu etkinleştir"""
        # Route ID'nin gerçekten bir point merge'e ait olduğunu kontrol et
        route_found = False
        for route in self.drawn_elements.get('routes', []):
            if route.get('id') == route_id:
                route_type = route.get('type', route.get('config', {}).get('pattern_type', ''))
                if route_type == 'pointmerge':
                    route_found = True
                    print(f"Geçerli point merge bulundu, ID: {route_id}, taşıma modu başlatılıyor")
                    self._start_route_move_mode(route_id)
                else:
                    print(f"HATA: {route_id} ID'li rota bir point merge değil! Tip: {route_type}")
                break
                
        if not route_found:
            print(f"HATA: {route_id} ID'li point merge bulunamadı")
        
    def _on_route_rotate_requested(self, route_id):
        """User Route döndürme modunu etkinleştir"""
        # Route ID'nin gerçekten bir user_route'a ait olduğunu kontrol et
        route_found = False
        selected_route = None
        route_index = -1
        
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                route_type = route.get('type', '')
                if route_type == 'user_route':
                    route_found = True
                    selected_route = route
                    route_index = i
                    print(f"Geçerli user route bulundu, ID: {route_id}")
                else:
                    print(f"HATA: {route_id} ID'li rota bir user_route değil! Tip: {route_type}")
                break
                
        if not route_found or not selected_route:
            print(f"HATA: {route_id} ID'li user route bulunamadı")
            return
            
        # Eğer rota bulunduysa, döndürme merkezi seçim dialogunu göster
        if selected_route and 'points' in selected_route and len(selected_route['points']) > 0:
            # Rotadaki noktaları göster ve kullanıcının döndürme merkezini seçmesini sağla
            dialog = RotationCenterDialog(selected_route['points'], self)
            
            # Dialog'u uygun bir konumda göster
            screen_center = QPointF(self.width() / 2, self.height() / 2)
            dialog.move(self.mapToGlobal(screen_center.toPoint()))
            
            # Dialog'un sonucuna göre işlem yap
            if dialog.exec_() == QDialog.Accepted:
                selected_point_index = dialog.selected_point_index
                print(f"Döndürme merkezi seçildi: Waypoint {selected_point_index + 1}")
                self._start_route_rotate_mode(route_id, center_point_index=selected_point_index)
            else:
                print("Döndürme merkezi seçimi iptal edildi")
        else:
            print(f"HATA: {route_id} ID'li rotada waypoint bulunamadı")
    
    def _on_trombone_rotate_requested(self, route_id):
        """Trombone döndürme modunu etkinleştir"""
        # ID formatı kontrolü ekle
        if not route_id.startswith("trombone_") and not "_" in route_id:
            print(f"UYARI: {route_id} ID'si bir trombone formatında değil. 'trombone_' önekiyle başlaması beklenir.")
            
        # Route ID'nin gerçekten bir trombone'a ait olduğunu kontrol et
        route_found = False
        selected_route = None
        route_index = -1
        
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                route_type = route.get('type', route.get('config', {}).get('pattern_type', ''))
                if route_type == 'trombone':
                    route_found = True
                    selected_route = route
                    route_index = i
                    print(f"Geçerli trombone bulundu, ID: {route_id}")
                else:
                    print(f"HATA: {route_id} ID'li rota bir trombone değil! Tip: {route_type}")
                break
                
        if not route_found or not selected_route:
            print(f"HATA: {route_id} ID'li trombone bulunamadı")
            return
            
        # Eğer rota bulunduysa, döndürme merkezi seçim dialogunu göster
        if selected_route and 'points' in selected_route and len(selected_route['points']) > 0:
            # Rotadaki noktaları göster ve kullanıcının döndürme merkezini seçmesini sağla
            dialog = RotationCenterDialog(selected_route['points'], self)
            
            # Dialog'u uygun bir konumda göster
            screen_center = QPointF(self.width() / 2, self.height() / 2)
            dialog.move(self.mapToGlobal(screen_center.toPoint()))
            
            # Dialog'un sonucuna göre işlem yap
            if dialog.exec_() == QDialog.Accepted:
                selected_point_index = dialog.selected_point_index
                print(f"Döndürme merkezi seçildi: Waypoint {selected_point_index + 1}")
                self._start_route_rotate_mode(route_id, center_point_index=selected_point_index)
            else:
                print("Döndürme merkezi seçimi iptal edildi")
        else:
            print(f"HATA: {route_id} ID'li trombone'da waypoint bulunamadı")
    
    def _on_pointmerge_rotate_requested(self, route_id):
        """Point Merge döndürme modunu etkinleştir"""
        # Route ID'nin gerçekten bir point merge'e ait olduğunu kontrol et
        route_found = False
        selected_route = None
        route_index = -1
        
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                route_type = route.get('type', route.get('config', {}).get('pattern_type', ''))
                if route_type == 'pointmerge':
                    route_found = True
                    selected_route = route
                    route_index = i
                    print(f"Geçerli point merge bulundu, ID: {route_id}")
                else:
                    print(f"HATA: {route_id} ID'li rota bir point merge değil! Tip: {route_type}")
                break
                
        if not route_found or not selected_route:
            print(f"HATA: {route_id} ID'li point merge bulunamadı")
            return
            
        # Eğer rota bulunduysa, döndürme merkezi seçim dialogunu göster
        if selected_route and 'points' in selected_route and len(selected_route['points']) > 0:
            # Rotadaki noktaları göster ve kullanıcının döndürme merkezini seçmesini sağla
            dialog = RotationCenterDialog(selected_route['points'], self)
            
            # Dialog'u uygun bir konumda göster
            screen_center = QPointF(self.width() / 2, self.height() / 2)
            dialog.move(self.mapToGlobal(screen_center.toPoint()))
            
            # Dialog'un sonucuna göre işlem yap
            if dialog.exec_() == QDialog.Accepted:
                selected_point_index = dialog.selected_point_index
                print(f"Döndürme merkezi seçildi: Waypoint {selected_point_index + 1}")
                self._start_route_rotate_mode(route_id, center_point_index=selected_point_index)
            else:
                print("Döndürme merkezi seçimi iptal edildi")
        else:
            print(f"HATA: {route_id} ID'li point merge'de waypoint bulunamadı")
    
    def _start_route_move_mode(self, route_id):
        """Rota taşıma modunu başlat"""
        # İlgili rotayı bul
        route_found = False
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                # Mevcut taşıma/döndürme modlarını resetle
                self.route_move_mode = False
                self.route_rotate_mode = False
                self.route_being_moved = None
                self.route_being_rotated = None
                
                # Taşıma modunu etkinleştir
                self.route_move_mode = True
                self.route_being_moved = route_id
                self.selected_path_index = i
                self.setCursor(Qt.ClosedHandCursor)  # El imlecini göster
                
                # Rota tipini belirle ve uygun mesaj göster
                route_type = route.get('type', '')
                type_str = "Trombone" if route_type == 'trombone' else "Point Merge" if route_type == 'pointmerge' else "Rota"
                self.update_status_message(f"{type_str} TAŞIMA MODU: {route_id} rotasını taşımak için sürükleyin - Bitirmek için fare tuşunu bırakın")
                
                print(f"Taşıma modu başlatıldı - {route_type} rotası: {route_id}")
                route_found = True
                break
        
        if not route_found:
            print(f"Hata: {route_id} ID'li rota bulunamadı!")
    
    def _start_route_rotate_mode(self, route_id, center_point_index=None):
        """Rota döndürme modunu başlat"""
        # İlgili rotayı bul
        route_found = False
        for i, route in enumerate(self.drawn_elements.get('routes', [])):
            if route.get('id') == route_id:
                # Mevcut taşıma/döndürme modlarını resetle
                self.route_move_mode = False
                self.route_rotate_mode = False
                self.route_being_moved = None
                self.route_being_rotated = None
                
                self.route_rotate_mode = True
                self.route_being_rotated = route_id
                self.selected_path_index = i
                
                # Döndürme için referans merkez noktası belirle
                route_type = route.get('type', '')
                if route_type == 'pointmerge':
                    # Point merge için kullanıcının seçtiği noktayı veya varsayılan olarak merge point'i merkez al
                    if len(route['points']) > 0:
                        if center_point_index is not None and center_point_index < len(route['points']):
                            # Kullanıcının seçtiği noktayı merkez al
                            center_lat, center_lon = route['points'][center_point_index]
                            print(f"Point Merge için seçilen rotasyon merkezi: Waypoint {center_point_index + 1}")
                        else:
                            # Varsayılan olarak merge point'i (son nokta) merkez al
                            center_lat, center_lon = route['points'][-1]  # Son nokta (merge point)
                            print(f"Point Merge için varsayılan rotasyon merkezi (merge point) kullanılıyor")
                        self.rotate_center_lat_lon = (center_lat, center_lon)
                elif route_type == 'trombone':
                    # Trombone için kullanıcının seçtiği noktayı veya varsayılan olarak son noktayı merkez al
                    if len(route['points']) > 0:
                        if center_point_index is not None and center_point_index < len(route['points']):
                            # Kullanıcının seçtiği noktayı merkez al
                            center_lat, center_lon = route['points'][center_point_index]
                            print(f"Trombone için seçilen rotasyon merkezi: Waypoint {center_point_index + 1}")
                        else:
                            # Varsayılan olarak son noktayı (pist yaklaşım noktası) döndürme merkezi olarak kullan
                            center_lat, center_lon = route['points'][-1]  # Son nokta
                            print(f"Trombone için varsayılan rotasyon merkezi (son nokta) kullanılıyor")
                        self.rotate_center_lat_lon = (center_lat, center_lon)
                else:
                    # Normal rotalar için kullanıcının seçtiği noktayı ya da varsayılan olarak ilk noktayı merkez al
                    if len(route['points']) > 0:
                        if center_point_index is not None and center_point_index < len(route['points']):
                            # Kullanıcının seçtiği noktayı merkez al
                            center_lat, center_lon = route['points'][center_point_index]
                        else:
                            # Varsayılan olarak ilk noktayı merkez al
                            center_lat, center_lon = route['points'][0]
                            
                        self.rotate_center_lat_lon = (center_lat, center_lon)
                        print(f"Rota rotasyon merkezi belirlendi: Waypoint {center_point_index + 1 if center_point_index is not None else 1}, lat={center_lat}, lon={center_lon}")
                
                self.setCursor(Qt.CrossCursor)  # Döndürme işlemi için çapraz imleç
                
                # Rota tipini belirle ve uygun mesaj göster
                type_str = "Trombone" if route_type == 'trombone' else "Point Merge" if route_type == 'pointmerge' else "Rota"
                self.update_status_message(f"{type_str} DÖNDÜRME MODU: {route_id} rotasını döndürmek için sürükleyin - Bitirmek için fare tuşunu bırakın")
                
                print(f"Döndürme modu başlatıldı - {route_type} rotası: {route_id}")
                route_found = True
                break
                
        if not route_found:
            print(f"Hata: {route_id} ID'li rota bulunamadı!")

    def draw_waypoints(self, painter):
        """Draw all waypoints on the map if they are set to be visible"""
        if not self.show_waypoints or not hasattr(self, 'data_manager') or not self.data_manager.waypoint_coords:
            return  # Waypoints are not visible or no data manager available
            
        # Get waypoint display settings from data manager
        display = self.data_manager.waypoint_display
        size = display.get('size', 6)
        color = QColor(display.get('color', '#3388ff'))
        border_color = QColor(display.get('border_color', '#000000'))
        border_width = display.get('border_width', 1)
        show_labels = display.get('show_labels', True)
        label_font_size = display.get('label_font_size', 10)
        
        # Set up painter for waypoints
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(color))
        
        # Draw each waypoint
        for name, coords in self.data_manager.waypoint_coords.items():
            lat, lon = coords
            screen_pos = self.geo_to_screen(lat, lon)
            
            # Draw the waypoint marker
            painter.drawEllipse(screen_pos, size, size)
            
            # Draw the waypoint label if enabled
            if show_labels:
                painter.setPen(QPen(border_color, 1))
                # Save current font to restore later
                old_font = painter.font()
                font = painter.font()
                font.setPointSize(label_font_size)
                painter.setFont(font)
                
                # Draw text with a small offset from the waypoint
                text_pos = QPointF(screen_pos.x() + size + 2, screen_pos.y() - size)
                painter.drawText(text_pos, name)
                
                # Restore the original font
                painter.setFont(old_font)
                
        # Restore painter state
        painter.setPen(QPen(Qt.black, 1))

    def set_data_manager(self, data_manager):
        """Set the data manager reference for accessing waypoints and other data"""
        self.data_manager = data_manager

    def _on_drawings_save_to_json(self, filepath):
        """Save all drawings (trombone, point-merge, routes) to a JSON file."""
        try:
            drawings_data = {
                'routes': self.drawn_elements['routes']
            }
            
            from json_utils import json_dumps
            with open(filepath, 'w', encoding='utf-8') as f:
                json_data = json_dumps(drawings_data, indent=4)
                f.write(json_data)
            
            self.update_status_message(f"Çizimler başarıyla kaydedildi: {filepath}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Kaydetme Hatası", f"Çizimleri kaydetme hatası: {str(e)}")
            return False
    
    def _on_drawings_load_from_json(self, filepath):
        """Load drawings (trombone, point-merge, routes) from a JSON file."""
        try:
            from json_utils import json_loads
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = f.read()
                drawings_data = json_loads(json_data)
            
            if 'routes' in drawings_data:
                loaded_routes = drawings_data['routes']
                # Mevcut rotalara ekle
                self.drawn_elements['routes'].extend(loaded_routes)
                self.update()
                self.update_status_message(f"{len(loaded_routes)} çizim yüklendi")
                return True
            else:
                QMessageBox.warning(self, "Yükleme Uyarısı", "JSON dosyasında çizim bulunamadı")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Yükleme Hatası", f"Çizimleri yükleme hatası: {str(e)}")
            return False

    def clear_all_drawings(self):
        """Clear all drawings from the map (routes, trajectories, waypoints)"""
        # Clear route selection if any
        self.selected_path_index = None
        
        # Clear all drawing lists
        self.drawn_elements['routes'] = []
        self.drawn_elements['trajectories'] = []
        self.drawn_elements['waypoints'] = []
        
        # Reset route drawing state (if active)
        if self.route_drawing_mode:
            self.route_drawing_mode = False
            self.current_route_points = []
            self.route_drawer.cancel_drawing()
            
        # Clear any active route movement or rotation mode
        self.route_move_mode = False
        self.route_rotate_mode = False
        self.route_being_moved = None
        self.route_being_rotated = None
        
        # Update the display
        self.update()
        self.update_status_message("Tüm çizimler temizlendi")

    def set_multi_select_mode(self, enabled):
        """Enable or disable multi select mode for routes"""
        self.multi_select_mode = enabled
        if not enabled:
            # Multi-select modu kapatıldığında seçimleri temizle
            self.selected_route_indices = []
        self.update()
    
    def toggle_route_selection(self, index):
        """Add or remove a route from the selection in multi-select mode"""
        if index in self.selected_route_indices:
            self.selected_route_indices.remove(index)
        else:
            self.selected_route_indices.append(index)
        self.update()
    
    def merge_selected_routes(self):
        """Merge all selected routes into a single route"""
        if not self.selected_route_indices or len(self.selected_route_indices) < 2:
            return False
            
        # Birleştirilecek rotaları sıralı şekilde topla
        sorted_indices = sorted(self.selected_route_indices)
        routes_to_merge = [self.drawn_elements['routes'][i] for i in sorted_indices]
        
        # Akıllı birleştirme: Eğer noktalar yakınsa birleştir, değilse ayrı nokta olarak ekle
        all_points = []
        route_breaks = []  # Hangi indekslerde rota kırılması olduğunu kaydet
        
        # İlk rotanın tüm noktalarını ekle
        first_route = routes_to_merge[0]
        all_points.extend(first_route['points'])
        
        # Birleştirme toleransı (iki nokta bu mesafeden yakınsa aynı kabul edilir)
        MERGE_TOLERANCE = 0.0001  # Yaklaşık 10-15 metre (enlem/boylam değeri olarak)
        
        # Sonraki rotalar için, eğer son nokta ile ilk nokta aynı değilse her ikisini de ekle
        for i in range(1, len(routes_to_merge)):
            current_route = routes_to_merge[i]
            
            if not current_route['points']:
                continue  # Boş rota ise atla
                
            # Önceki rotanın son noktası ve mevcut rotanın ilk noktası
            prev_last_point = all_points[-1]
            curr_first_point = current_route['points'][0]
            
            # İki nokta arasındaki mesafeyi hesapla
            from utils import calculate_distance
            distance = calculate_distance(prev_last_point[0], prev_last_point[1], 
                                         curr_first_point[0], curr_first_point[1])
            
            # Eğer noktalar yeterince yakın değilse, yeni noktayı da ekle
            # Bu, snap edilmemiş noktaları birleştirmemeyi sağlar
            if distance > MERGE_TOLERANCE:
                # Rota kırılması olduğunu işaretle - bu noktadan önceki segment gösterilmeyecek
                route_breaks.append(len(all_points))
                all_points.extend(current_route['points'])
            else:
                # Noktalar çok yakınsa, ilk noktayı atlayıp diğer noktaları ekle
                all_points.extend(current_route['points'][1:])
        
        # Benzersiz ID oluştur
        merged_route_id = f"route_{self.route_id_counter}"
        self.route_id_counter += 1
        
        # Noktalar için benzersiz isimler oluştur
        waypoint_names = [f"WP{i+1}" for i in range(len(all_points))]
        
        # Mesafeleri hesapla
        segment_distances = self.calculate_segment_distances(all_points)
        
        # Rota kırılma noktalarındaki segmentlerin mesafesini -1 olarak işaretle
        # Bu segmentler çizilmeyecek
        for break_index in route_breaks:
            if 0 < break_index < len(all_points):
                segment_distances[break_index-1] = -1  # Kırık noktasından önceki segment
        
        # Yeni birleşik rota oluştur
        merged_route = {
            'type': 'user_route',
            'id': merged_route_id,
            'points': all_points,
            'waypoint_names': waypoint_names,
            'segment_distances': segment_distances,
            'name': f"Merged Route {self.route_id_counter}"
        }
        
        # Birleştirilen rotaları kaldır (sondan başa doğru silmek gerekir ki indeksler kaymasın)
        for index in sorted(self.selected_route_indices, reverse=True):
            self.drawn_elements['routes'].pop(index)
        
        # Yeni rotayı ekle
        self.drawn_elements['routes'].append(merged_route)
        
        # Seçimleri temizle
        self.selected_route_indices = []
        self.selected_path_index = len(self.drawn_elements['routes']) - 1  # Yeni eklenen rotayı seç
        
        self.update()
        return True
    
    def delete_selected_routes(self):
        """Delete all selected routes"""
        if not self.selected_route_indices:
            return False
            
        # Seçilen rotaları kaldır (sondan başa doğru)
        for index in sorted(self.selected_route_indices, reverse=True):
            if 0 <= index < len(self.drawn_elements['routes']):
                self.drawn_elements['routes'].pop(index)
        
        # Seçimleri temizle
        self.selected_route_indices = []
        self.selected_path_index = -1  # Hiçbir rota seçili değil
        
        self.update()
        return True

    def _check_and_update_waypoint_name(self, route_index, waypoint_index, lat, lon):
        """
        Waypoint taşındığında ismini otomatik olarak kontrol eder ve günceller.
        Eğer bir waypoint'in üzerine snap edilmişse o waypoint'in ismini alır.
        Eğer bir waypoint'ten uzaklaşmışsa ve mevcut isim bir gerçek waypoint ismi ise, 
        orijinal formata (WP1, PM2 vb.) döndürür.
        
        Args:
            route_index (int): Rota indeksi
            waypoint_index (int): Waypoint indeksi
            lat (float): Yeni latitude değeri
            lon (float): Yeni longitude değeri
            
        Returns:
            bool: İsim değiştiyse True, değişmediyse False
        """
        if 'waypoint_names' not in self.drawn_elements['routes'][route_index]:
            return False
        
        route = self.drawn_elements['routes'][route_index]
        waypoint_names = route.get('waypoint_names', [])
        
        # Eğer waypoint_names listesi, points listesinden kısa ise genişlet
        while len(waypoint_names) <= waypoint_index:
            prefix = "WP"  # Varsayılan prefix
            if 'pointmerge' in route.get('id', ''):
                prefix = "PM"
            elif 'trombone' in route.get('id', ''):
                prefix = "T"
                
            waypoint_names.append(f"{prefix}{len(waypoint_names)+1}")
            
        current_name = waypoint_names[waypoint_index]
        
        # Yeni konumda bir waypoint var mı kontrol et
        new_name = None
        if hasattr(self, 'data_manager') and hasattr(self.data_manager, 'waypoint_coords'):
            # Tam waypoint eşleşmesi için kontrol et
            for name, coords in self.data_manager.waypoint_coords.items():
                w_lat, w_lon = coords
                # Hassas koordinat karşılaştırması (6 ondalık basamak)
                if abs(w_lat - lat) < 0.000001 and abs(w_lon - lon) < 0.000001:
                    new_name = name
                    break
            
            # Eğer bir waypoint üzerindeyse, o ismi kullan
            if new_name:
                if current_name != new_name:
                    waypoint_names[waypoint_index] = new_name
                    self.update_status_message(f"Waypoint ismi '{current_name}' -> '{new_name}' olarak güncellendi")
                    return True
            
            # Şu an bir waypoint üzerinde değiliz, ancak önceki isim bir waypoint ismi miydi?
            elif current_name in self.data_manager.waypoint_coords:
                # Önceki isim gerçek bir waypoint ismi idi, şimdi orijinal formata döndür
                prefix = "WP"  # Varsayılan prefix
                if 'pointmerge' in route.get('id', ''):
                    prefix = "PM"
                elif 'trombone' in route.get('id', ''):
                    prefix = "T"
                
                new_name = f"{prefix}{waypoint_index+1}"
                waypoint_names[waypoint_index] = new_name
                self.update_status_message(f"Waypoint ismi '{current_name}' -> '{new_name}' olarak güncellendi")
                return True
                
        return False