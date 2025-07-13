from PyQt5.QtCore import Qt, QObject, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush
import math

class SnapPoint:
    """Snap noktalarını temsil eden sınıf"""
    
    def __init__(self, screen_pos, geo_pos, description, point_type):
        self.screen_pos = screen_pos  # Ekran koordinatları (QPointF)
        self.geo_pos = geo_pos        # Coğrafi koordinatlar (lat, lon)
        self.description = description # Açıklama (örn. "Rota uç noktası", "Rota orta noktası")
        self.point_type = point_type  # Nokta tipi (endpoint, midpoint, intersection vb.)
    
    def distance_to(self, pos):
        """Verilen pozisyonla snap noktası arasındaki mesafeyi hesapla"""
        return (self.screen_pos - pos).manhattanLength()

class SnapManager(QObject):
    """Snap işlevlerini yöneten sınıf"""
    
    # Snap modları
    SNAP_NONE = 0
    SNAP_ENDPOINT = 1
    SNAP_MIDPOINT = 2
    SNAP_INTERSECTION = 4
    SNAP_WAYPOINT = 16  # Yeni: Waypoint'ler için snap modu
    SNAP_ALL = 23  # Tüm modlar aktif (23 = 1+2+4+16)
    
    # Renk sabitleri
    SNAP_POINT_COLOR = QColor(255, 255, 0)  # Sarı
    SNAP_HIGHLIGHT_COLOR = QColor(255, 165, 0)  # Turuncu
    SNAP_TEXT_COLOR = QColor(255, 255, 255)  # Beyaz
    SNAP_TEXT_BG_COLOR = QColor(0, 0, 0, 180)  # Yarı saydam siyah
    
    def __init__(self, map_widget):
        super().__init__()
        self.map_widget = map_widget
        
        # Snap ayarları
        self.snap_enabled = True
        
        # Başlangıçta waypoint görünürlüğüne bağlı olarak snap modunu ayarla
        base_mode = self.SNAP_ENDPOINT | self.SNAP_MIDPOINT  # Temel snap modları (3)
        
        # Eğer map_widget'ta waypoints görünür durumdaysa, SNAP_WAYPOINT'i aktifleştir
        if hasattr(map_widget, 'show_waypoints') and map_widget.show_waypoints:
            self.snap_mode = base_mode | self.SNAP_WAYPOINT  # 19 (3 + 16)
        else:
            self.snap_mode = base_mode  # 3
            
        self.snap_tolerance = 15  # Piksel cinsinden yakalama toleransı
        
        # Çalışma verileri
        self.current_mouse_pos = None
        self.snap_points = []  # Mevcut fare pozisyonu için bulunan yakalama noktaları
        self.active_snap_point = None  # Aktif olarak yakalanan nokta (en yakın)
    
    def set_snap_mode(self, mode):
        """Snap modunu ayarla"""
        self.snap_mode = mode
    
    def set_snap_enabled(self, enabled):
        """Snap özelliğini etkinleştir/devre dışı bırak"""
        self.snap_enabled = enabled
    
    def set_snap_tolerance(self, tolerance):
        """Yakalama toleransını piksel cinsinden ayarla"""
        self.snap_tolerance = max(5, min(50, tolerance))  # 5-50 piksel aralığında sınırla
    
    def update_mouse_position(self, mouse_pos, force_find_snaps=False):
        """Fare pozisyonunu güncelle ve snap noktalarını bul"""
        self.current_mouse_pos = mouse_pos
        
        # Eğer snap devre dışıysa, aktif nokta temizlenir
        if not self.snap_enabled:
            self.active_snap_point = None
            self.snap_points = []
            return None
        
        # Snap noktalarını bul
        self.find_snap_points(mouse_pos)
        
        # En yakın snap noktasını bul
        self.active_snap_point = self.find_closest_snap_point(mouse_pos)
        
        return self.active_snap_point
        
    def find_snap_points(self, mouse_pos):
        """Mevcut fare pozisyonu için olası snap noktalarını bul"""
        self.snap_points = []
        
        if not self.snap_enabled:
            return
        
        # Uç noktalar ve orta noktalar için snap noktaları bul
        if self.snap_mode & self.SNAP_ENDPOINT or self.snap_mode & self.SNAP_MIDPOINT:
            self._find_route_snap_points(mouse_pos)
        
        # Kesişim noktaları için snap noktaları bul
        if self.snap_mode & self.SNAP_INTERSECTION:
            self._find_intersection_snap_points(mouse_pos)
            
        # Waypoint noktalarına snap bul
        if self.snap_mode & self.SNAP_WAYPOINT:
            self._find_waypoint_snap_points(mouse_pos)
    
    def _find_route_snap_points(self, mouse_pos):
        """Rotalardaki end point ve midpoint gibi yakalama noktalarını bul"""
        if not hasattr(self.map_widget, 'drawn_elements') or 'routes' not in self.map_widget.drawn_elements:
            return
            
        # Tüm rotaları kontrol et
        for route in self.map_widget.drawn_elements['routes']:
            if 'points' not in route:
                continue
                
            points = route['points']
            
            # Uç noktaları kontrol et
            if self.snap_mode & self.SNAP_ENDPOINT:
                for i, point in enumerate(points):
                    lat, lon = point
                    screen_pos = self.map_widget.geo_to_screen(lat, lon)
                    
                    # Fare pozisyonuna yeterince yakınsa, snap noktası olarak ekle
                    if (screen_pos - mouse_pos).manhattanLength() <= self.snap_tolerance * 2:  # Biraz daha geniş tarama
                        desc = f"Uç nokta: {route.get('waypoint_names', [])[i] if 'waypoint_names' in route and i < len(route.get('waypoint_names', [])) else f'Nokta {i+1}'}"
                        self.snap_points.append(SnapPoint(screen_pos, (lat, lon), desc, "endpoint"))
            
            # Orta noktaları kontrol et
            if self.snap_mode & self.SNAP_MIDPOINT and len(points) > 1:
                for i in range(len(points) - 1):
                    lat1, lon1 = points[i]
                    lat2, lon2 = points[i + 1]
                    
                    # Orta nokta hesapla (hem coğrafi hem de ekran koordinatlarında)
                    mid_lat = (lat1 + lat2) / 2
                    mid_lon = (lon1 + lon2) / 2
                    mid_screen = self.map_widget.geo_to_screen(mid_lat, mid_lon)
                    
                    # Fare pozisyonuna yeterince yakınsa, snap noktası olarak ekle
                    if (mid_screen - mouse_pos).manhattanLength() <= self.snap_tolerance * 2:
                        desc = f"Orta nokta: Segment {i+1}-{i+2}"
                        self.snap_points.append(SnapPoint(mid_screen, (mid_lat, mid_lon), desc, "midpoint"))
    

    def _find_intersection_snap_points(self, mouse_pos):
        """Rota kesişim noktalarını bul"""
        if not hasattr(self.map_widget, 'drawn_elements') or 'routes' not in self.map_widget.drawn_elements:
            return
            
        # Tüm route çiftleri için kesişimleri kontrol et
        routes = self.map_widget.drawn_elements['routes']
        for i in range(len(routes)):
            if 'points' not in routes[i] or len(routes[i]['points']) < 2:
                continue
                
            for j in range(i + 1, len(routes)):
                if 'points' not in routes[j] or len(routes[j]['points']) < 2:
                    continue
                    
                # Her iki rotadaki tüm segment çiftleri için kesişimleri kontrol et
                for seg1_idx in range(len(routes[i]['points']) - 1):
                    for seg2_idx in range(len(routes[j]['points']) - 1):
                        # Segment 1 noktaları
                        p1 = routes[i]['points'][seg1_idx]
                        p2 = routes[i]['points'][seg1_idx + 1]
                        
                        # Segment 2 noktaları
                        p3 = routes[j]['points'][seg2_idx]
                        p4 = routes[j]['points'][seg2_idx + 1]
                        
                        # Ekran koordinatlarına dönüştür
                        s1 = self.map_widget.geo_to_screen(p1[0], p1[1])
                        s2 = self.map_widget.geo_to_screen(p2[0], p2[1])
                        s3 = self.map_widget.geo_to_screen(p3[0], p3[1])
                        s4 = self.map_widget.geo_to_screen(p4[0], p4[1])
                        
                        # Ekran koordinatlarında kesişim noktasını bul
                        intersection = self._line_intersection(
                            (s1.x(), s1.y()), (s2.x(), s2.y()),
                            (s3.x(), s3.y()), (s4.x(), s4.y())
                        )
                        
                        if intersection:
                            ix, iy = intersection
                            intersect_screen = QPointF(ix, iy)
                            
                            # Kesişim noktası fare yakınında mı?
                            if (intersect_screen - mouse_pos).manhattanLength() <= self.snap_tolerance * 2:
                                # Ekran koordinatlarını coğrafi koordinatlara çevir
                                lat, lon = self.map_widget.screen_to_geo(ix, iy)
                                desc = f"Kesişim: Rota {i+1} - Rota {j+1}"
                                self.snap_points.append(SnapPoint(intersect_screen, (lat, lon), desc, "intersection"))
    
    def _line_intersection(self, p1, p2, p3, p4):
        """İki çizgi parçası arasında kesişim noktası hesapla"""
        # Line segment intersection using parametric equation
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        
        # Çizgiler paralellik kontrolü
        if abs(denom) < 1e-8:
            return None
        
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        
        # Kesişim segment içinde mi kontrol et
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return (x, y)
        
        return None
    
    def _find_waypoint_snap_points(self, mouse_pos):
        """Waypoint noktalarını snap noktaları olarak bul"""
        # Harita widget'inin data_manager'a ve waypoint koordinatlarına erişimi olduğundan emin ol
        if not hasattr(self.map_widget, 'data_manager') or not hasattr(self.map_widget.data_manager, 'waypoint_coords'):
            return
            
        waypoint_coords = self.map_widget.data_manager.waypoint_coords
        if not waypoint_coords:
            return
            
        # Tüm waypoint'leri kontrol et
        for waypoint_name, coords in waypoint_coords.items():
            lat, lon = coords
            screen_pos = self.map_widget.geo_to_screen(lat, lon)
            
            # Fare pozisyonuna yeterince yakınsa, snap noktası olarak ekle
            if (screen_pos - mouse_pos).manhattanLength() <= self.snap_tolerance * 2:  # Biraz daha geniş tarama
                desc = f"Waypoint: {waypoint_name}"
                self.snap_points.append(SnapPoint(screen_pos, (lat, lon), desc, "waypoint"))
    
    def find_closest_snap_point(self, mouse_pos):
        """En yakın snap noktasını bul"""
        if not self.snap_points:
            return None
            
        closest = None
        min_dist = float('inf')
        
        for snap_point in self.snap_points:
            dist = snap_point.distance_to(mouse_pos)
            if dist < min_dist and dist <= self.snap_tolerance:
                min_dist = dist
                closest = snap_point
                
        return closest
    
    def paint_snap_indicators(self, painter):
        """Snap göstergelerini çiz"""
        if not self.snap_enabled or not self.current_mouse_pos:
            return
            
        # Aktif snap noktası varsa, onu vurgula
        if self.active_snap_point:
            # Snap noktası vurgu halkasını çiz
            painter.setPen(QPen(self.SNAP_HIGHLIGHT_COLOR, 2, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)
            snap_pos = self.active_snap_point.screen_pos
            painter.drawEllipse(snap_pos, 8, 8)
            
            # Kesikli artı işareti çiz
            dash_pen = QPen(self.SNAP_HIGHLIGHT_COLOR, 1, Qt.DashLine)
            dash_pen.setDashPattern([3, 3])
            painter.setPen(dash_pen)
            
            # QPointF nesneleri oluşturarak drawLine fonksiyonunu çağır
            p1_horizontal = QPointF(snap_pos.x() - 15, snap_pos.y())
            p2_horizontal = QPointF(snap_pos.x() + 15, snap_pos.y())
            painter.drawLine(p1_horizontal, p2_horizontal)
            
            p1_vertical = QPointF(snap_pos.x(), snap_pos.y() - 15)
            p2_vertical = QPointF(snap_pos.x(), snap_pos.y() + 15)
            painter.drawLine(p1_vertical, p2_vertical)
            
            # Açıklama metnini çiz
            self._draw_snap_info_text(painter, self.active_snap_point)
    
    def _draw_snap_info_text(self, painter, snap_point):
        """Snap noktası bilgi metnini çiz"""
        if not snap_point:
            return
            
        text = snap_point.description
        pos = snap_point.screen_pos
        
        # Metin için eski font ayarlarını sakla
        old_font = painter.font()
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Metin boyutunu hesapla
        text_rect = painter.fontMetrics().boundingRect(text)
        
        # Metin arkaplanı için dikdörtgen
        bg_rect = text_rect.adjusted(-4, -2, 4, 2)
        bg_rect.moveCenter(pos.toPoint())
        bg_rect.moveTop(int(pos.y() - bg_rect.height() - 10))  # Noktanın 10px üstüne
        
        # Arkaplan çiz
        painter.setBrush(QBrush(self.SNAP_TEXT_BG_COLOR))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 3, 3)
        
        # Metni çiz
        painter.setPen(QPen(self.SNAP_TEXT_COLOR))
        painter.drawText(
            bg_rect, 
            Qt.AlignCenter, 
            text
        )
        
        # Eski font ayarlarını geri yükle
        painter.setFont(old_font)
        
    def get_snapped_position(self, mouse_pos):
        """Fare pozisyonuna göre yakalanan pozisyonu döndür"""
        self.update_mouse_position(mouse_pos)
        
        if self.active_snap_point:
            return self.active_snap_point.geo_pos
        else:
            # Yakalama yoksa orijinal konumu döndür
            return self.map_widget.screen_to_geo(mouse_pos.x(), mouse_pos.y())
