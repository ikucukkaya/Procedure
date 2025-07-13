from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QObject, QRectF
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush
import math
from snap_manager import SnapManager

class RouteDrawer(QObject):
    """Handles route drawing functionality for the map widget"""
    
    # Define signals at class level
    routeDrawingStarted = pyqtSignal()
    routeDrawingFinished = pyqtSignal(str, list)
    routePointAdded = pyqtSignal(list)  # Yeni waypoint eklendiğinde yayınlanan sinyal
    
    def __init__(self, map_widget):
        super().__init__()  # Initialize QObject
        self.map_widget = map_widget
        self.drawing_route = False
        self.current_route_points = []
        self.route_drawing_mode = False
        self.dragging_waypoint = False
        self.dragged_waypoint_index = None
        self.mouse_position = None  # Fare konumunu takip etmek için
        self.waypoint_names = []    # Waypoint isimlerini saklamak için
        
        # Snap yöneticisini oluştur
        self.snap_manager = SnapManager(map_widget)
        # Grid özelliği tamamen kaldırıldığından emin ol
        current_mode = self.snap_manager.snap_mode
        # Herhangi bir grid modu varsa çıkar (SNAP_GRID = 8 idi)
        if current_mode & 8:  # 8 = eski SNAP_GRID değeri
            self.snap_manager.set_snap_mode(current_mode & ~8)  # SNAP_GRID modunu çıkar
        
    def start_route_drawing(self):
        """Start route drawing mode"""
        self.route_drawing_mode = True
        self.current_route_points = []
        self.waypoint_names = []  # Waypoint isimlerini sıfırla
        
        # Snap özelliğinin etkin olduğundan emin ol
        if hasattr(self, 'snap_manager'):
            # Snap yöneticisi varsa, etkinleştir
            self.snap_manager.set_snap_enabled(True)
            # Kullanıcıya snap durumu hakkında bilgi ver
            self.map_widget.update_status_message("Rota çizimi aktif - Sol tık: Nokta ekle, Sağ tık: Tamamla, Orta düğme: Kaydır (Snap özelliği etkin)")
        
        self.map_widget.setCursor(Qt.CrossCursor)
        self.routeDrawingStarted.emit()
        
    def finish_route_drawing(self, route_id):
        """Finish and save the route drawing"""
        # Noktaları kopyala
        points = self.current_route_points.copy()
        
        # Normal rotalar için her zaman 'user_route' tipini kullan
        # Sadece waypoint isimlendirmesi için ön eki doğru ayarla
        route_type = 'user_route'  # Temel tip her zaman user_route olmalı
        
        # route_id içindeki özel prefixleri kontrol et (pointmerge veya trombone)
        # ancak ana tip yine de 'user_route' olmalı
        if 'pointmerge' in route_id:
            prefix = "PM"
        elif 'trombone' in route_id:
            prefix = "T"
        else:
            prefix = "WP"
        
        # Eğer çizim sırasında waypoint'lere snap ile isimler atanmışsa onları kullan
        if hasattr(self, 'waypoint_names') and len(self.waypoint_names) == len(points):
            waypoint_names = self.waypoint_names.copy()
            # Hala boş veya varsayılan olan waypoint isimleri için otomatik isim ata
            for i in range(len(waypoint_names)):
                if not waypoint_names[i] or waypoint_names[i].startswith("WP"):
                    waypoint_names[i] = f"{prefix}{i+1}"
        else:
            # Waypoint isimleri yoksa varsayılan isimleri kullan
            waypoint_names = [f"{prefix}{i+1}" for i in range(len(points))]
        
        # Rota segmentleri arasındaki mesafeleri ve açıları hesapla
        segment_distances = self.map_widget.calculate_segment_distances(points)
        segment_angles = self.map_widget.calculate_track_angles(points)
        
        route_config = {
            'type': route_type,  # Her zaman 'user_route' olarak ayarla
            'id': route_id,
            'points': points,
            'waypoint_names': waypoint_names,  # Waypoint isimleri
            'segment_distances': segment_distances,  # Segment mesafeleri
            'segment_angles': segment_angles,  # Segment açıları
            'name': f"Route {len(self.map_widget.drawn_elements['routes']) + 1}"
        }
        self.map_widget.drawn_elements['routes'].append(route_config)
        self.routeDrawingFinished.emit(route_id, self.current_route_points)
        self.cancel_route_drawing()
        
    def cancel_route_drawing(self):
        """Cancel route drawing"""
        self.route_drawing_mode = False
        self.current_route_points = []
        self.waypoint_names = []  # Waypoint isimlerini sıfırla
        self.mouse_position = None  # Fare pozisyonunu sıfırla
        self.map_widget.setCursor(Qt.ArrowCursor)
        self.map_widget.update()
        
    def handle_mouse_press(self, event):
        """Handle mouse press events during route drawing"""
        if self.route_drawing_mode:
            if event.button() == Qt.MiddleButton:
                # Use middle button for panning instead of shift+left click
                self.map_widget.is_panning = True
                self.map_widget.move_start_pos = event.pos()
                self.map_widget.move_start_lat, self.map_widget.move_start_lon = self.map_widget.screen_to_geo(event.pos().x(), event.pos().y())
                self.map_widget.setCursor(Qt.ClosedHandCursor)
                self.map_widget.update_status_message("Haritayı kaydırma - Orta düğmeyi sürükleyerek haritayı kaydırın")
                return
                
            if event.button() == Qt.LeftButton:
                
                # Check if we're clicking on an existing waypoint
                pos = event.pos()
                for i, (lat, lon) in enumerate(self.current_route_points):
                    screen_pos = self.map_widget.geo_to_screen(lat, lon)
                    if (screen_pos - pos).manhattanLength() < 10:  # 10 pixels tolerance
                        self.dragging_waypoint = True
                        self.dragged_waypoint_index = i
                        
                        # Waypoint taşıma başladığında Grid modunu devre dışı bırak
                        # Mevcut modu yedekle ve grid referansını kaldır
                        current_mode = self.snap_manager.snap_mode
                        if current_mode & 8:  # 8 = eski SNAP_GRID değeri
                            self.snap_manager.set_snap_mode(current_mode & ~8)  # SNAP_GRID modunu çıkar
                            
                        self.map_widget.setCursor(Qt.ClosedHandCursor)
                        return
                
                # If not clicking on existing waypoint, add new one
                # Eğer aktif bir snap noktası varsa, o noktaya yerleştir
                waypoint_name = None
                if self.snap_manager.active_snap_point:
                    lat, lon = self.snap_manager.active_snap_point.geo_pos
                    # Snap noktası türüne göre durumu bildir
                    snap_type = self.snap_manager.active_snap_point.point_type
                    self.map_widget.update_status_message(f"{snap_type.capitalize()} yakalandı - {self.snap_manager.active_snap_point.description}")
                    
                    # Eğer waypoint'e snap olunduysa, waypoint adını al
                    if snap_type == "waypoint":
                        waypoint_name = self._get_waypoint_name_if_snapped(lat, lon)
                else:
                    # Snap yoksa normal fare pozisyonunu kullan
                    lat, lon = self.map_widget.screen_to_geo(pos.x(), pos.y())
                
                self.current_route_points.append((lat, lon))
                
                # Waypoint adını ekle (eğer bir waypoint'e snap olunduysa)
                if waypoint_name:
                    # Waypoint adını ekle veya son eklenen noktanın adını güncelle
                    if len(self.waypoint_names) < len(self.current_route_points):
                        self.waypoint_names.append(waypoint_name)
                    else:
                        self.waypoint_names[len(self.current_route_points) - 1] = waypoint_name
                    
                    # Kullanıcıya bilgi ver
                    self.map_widget.update_status_message(f"Waypoint '{waypoint_name}' rotaya eklendi")
                
                # Waypoint isimlerini güncelle - çizim aşamasında gösterimi kolaylaştırır
                self._update_waypoint_names()
                
                self.map_widget.update()
                
                # Yeni bir waypoint eklendiğinde sinyal yayınla
                self.routePointAdded.emit(self.current_route_points)
                
            elif event.button() == Qt.RightButton:
                # Check if we're clicking on an existing waypoint to delete it
                pos = event.pos()
                for i, (lat, lon) in enumerate(self.current_route_points):
                    screen_pos = self.map_widget.geo_to_screen(lat, lon)
                    if (screen_pos - pos).manhattanLength() < 10:  # 10 pixels tolerance
                        del self.current_route_points[i]
                        
                        # Silinen noktaya karşılık gelen waypoint adını da sil
                        if i < len(self.waypoint_names):
                            del self.waypoint_names[i]
                        
                        # Waypoint isimlerini güncelle
                        self._update_waypoint_names()
                        
                        self.map_widget.update()
                        
                        # Waypoint silindiğinde sinyal yayınla
                        self.routePointAdded.emit(self.current_route_points)
                        return
                
                # If not clicking on a waypoint, finish route drawing
                if len(self.current_route_points) >= 2:
                    route_id = f"route_{len(self.map_widget.drawn_elements['routes'])}"
                    self.finish_route_drawing(route_id)
                else:
                    self.cancel_route_drawing()
                    
    def handle_mouse_move(self, event):
        """Handle mouse move events during route drawing"""
        # Her durumda güncel fare konumunu kaydet
        self.mouse_position = event.pos()
        
        # Snap noktalarını güncelle - snap_manager'i kullanarak
        if self.route_drawing_mode:
            self.snap_manager.update_mouse_position(event.pos())
            
        self.map_widget.update()  # Her fare hareketinde ekranı güncelle
        
        if self.map_widget.is_panning:
            # Handle panning
            delta_x = self.map_widget.move_start_pos.x() - event.pos().x()
            delta_y = self.map_widget.move_start_pos.y() - event.pos().y()
            
            # Convert screen deltas to geographic deltas
            scale = self.map_widget.get_scale()
            delta_lat = -delta_y / scale  # Negate delta_y for correct up-down movement
            delta_lon = delta_x / (scale * math.cos(math.radians(self.map_widget.center_lat)))
            
            # Update center coordinates
            self.map_widget.center_lat += delta_lat
            self.map_widget.center_lon += delta_lon
            
            # Update start position for next move
            self.map_widget.move_start_pos = event.pos()
            
            # Recompute paths with new center
            self.map_widget.compute_country_paths()
            self.map_widget.update()
        elif self.dragging_waypoint:
            # Waypoint taşırken grid modunun devre dışı olduğundan emin ol
            current_mode = self.snap_manager.snap_mode
            if current_mode & 8:  # 8 = eski SNAP_GRID değeri
                self.snap_manager.set_snap_mode(current_mode & ~8)  # SNAP_GRID modunu çıkar
                
            # Update waypoint position - eğer snap aktifse ve bir yakalama varsa
            # snap pozisyonunu kullan, değilse normal fare pozisyonunu kullan
            waypoint_name = None
            if self.snap_manager.active_snap_point:
                # Snap noktasına yakalanan konum
                lat, lon = self.snap_manager.active_snap_point.geo_pos
                
                # Eğer waypoint'e snap olunduysa, waypoint adını al
                if self.snap_manager.active_snap_point.point_type == "waypoint":
                    waypoint_name = self._get_waypoint_name_if_snapped(lat, lon)
            else:
                # Normal fare pozisyonu
                lat, lon = self.map_widget.screen_to_geo(event.pos().x(), event.pos().y())
                
            self.current_route_points[self.dragged_waypoint_index] = (lat, lon)
            
            # Eğer waypoint'e snap olunduysa waypoint adını güncelle
            if waypoint_name:
                # Waypoint adını ilgili indekse ekle veya güncelle
                if self.dragged_waypoint_index >= len(self.waypoint_names):
                    # Eğer waypoint_names listesi kısa ise genişlet
                    while len(self.waypoint_names) <= self.dragged_waypoint_index:
                        self.waypoint_names.append("")
                
                # Waypoint adını güncelle
                self.waypoint_names[self.dragged_waypoint_index] = waypoint_name
                
                # Kullanıcıya bilgi ver
                self.map_widget.update_status_message(f"Waypoint '{waypoint_name}' yakalandı")
            elif self.dragged_waypoint_index < len(self.waypoint_names):
                # Waypoint'ten uzaklaştıysa, ismi sıralı waypoint formatına geri döndür
                # Önce mevcut ismi kontrol et
                current_name = self.waypoint_names[self.dragged_waypoint_index]
                
                # Eğer snap noktasında değilse ve isim XML'den yüklenmiş bir waypoint ismi ise
                # ismi varsayılan formata döndür
                if not self.snap_manager.active_snap_point or self.snap_manager.active_snap_point.point_type != "waypoint":
                    # Mevcut ismin waypoint_coords'ta olup olmadığını kontrol et
                    is_real_waypoint = False
                    if hasattr(self.map_widget, 'data_manager') and hasattr(self.map_widget.data_manager, 'waypoint_coords'):
                        is_real_waypoint = current_name in self.map_widget.data_manager.waypoint_coords
                    
                    # Eğer gerçek bir waypoint ise ve şu anda bir waypoint'e snap edilmemişse, varsayılan isme döndür
                    if current_name and is_real_waypoint:
                        # Rotada kullanılan prefixin ne olduğunu belirle 
                        prefix = "WP"  # Varsayılan prefix
                        
                        # Rota türüne göre prefix belirle
                        for route in self.map_widget.drawn_elements.get('routes', []):
                            if 'points' in route and self.current_route_points == route['points']:
                                if 'pointmerge' in route.get('id', ''):
                                    prefix = "PM"
                                    break
                                elif 'trombone' in route.get('id', ''):
                                    prefix = "T"
                                    break
                        
                        # Orijinal ismi geri döndür (indeks+1 ile)
                        self.waypoint_names[self.dragged_waypoint_index] = f"{prefix}{self.dragged_waypoint_index+1}"
                        
                        # Kullanıcıya bilgi ver
                        self.map_widget.update_status_message(f"Waypoint ismi '{current_name}' -> '{self.waypoint_names[self.dragged_waypoint_index]}' olarak değiştirildi")
                # Eğer isim yoksa veya zaten varsayılan formatta (WPx vb.) ise değişiklik yapma
            
            self.map_widget.update()
            
            # Waypoint sürüklendiğinde sinyal yayınla
            self.routePointAdded.emit(self.current_route_points)
            
    def handle_mouse_release(self, event):
        """Handle mouse release events during route drawing"""
        if self.dragging_waypoint:
            # Taşıma tamamlandığında, son bir kez daha waypoint isimlerini güncelle
            # Bu özellikle fare sürüklenip bırakıldığında son durumu kontrol etmek için önemli
            if self.dragged_waypoint_index is not None:
                # Sürüklenen noktanın son koordinatlarını al
                if self.dragged_waypoint_index < len(self.current_route_points):
                    lat, lon = self.current_route_points[self.dragged_waypoint_index]
                    
                    # Nokta bir waypoint'e denk geliyor mu kontrol et
                    waypoint_name = self._get_waypoint_name_if_snapped(lat, lon)
                    
                    # Eğer waypoint'e denk geliyorsa, adını güncelle
                    if waypoint_name and self.dragged_waypoint_index < len(self.waypoint_names):
                        self.waypoint_names[self.dragged_waypoint_index] = waypoint_name
                    # Eğer daha önce waypoint ismi varsa ancak şu an snap yoksa, varsayılan isme dön
                    elif self.dragged_waypoint_index < len(self.waypoint_names):
                        current_name = self.waypoint_names[self.dragged_waypoint_index]
                        
                        # Mevcut ismin waypoint_coords'ta olup olmadığını kontrol et
                        is_real_waypoint = False
                        if hasattr(self.map_widget, 'data_manager') and hasattr(self.map_widget.data_manager, 'waypoint_coords'):
                            is_real_waypoint = current_name in self.map_widget.data_manager.waypoint_coords
                        
                        # Eğer gerçek bir waypoint ise ve şu anda bir waypoint'e snap edilmemişse, varsayılan isme döndür
                        if current_name and is_real_waypoint:
                            # Rota türüne göre prefix belirle
                            prefix = "WP"  # Varsayılan prefix
                            for route in self.map_widget.drawn_elements.get('routes', []):
                                if 'points' in route and self.current_route_points == route['points']:
                                    if 'pointmerge' in route.get('id', ''):
                                        prefix = "PM"
                                        break
                                    elif 'trombone' in route.get('id', ''):
                                        prefix = "T"
                                        break
                            
                            # Varsayılan isme döndür
                            self.waypoint_names[self.dragged_waypoint_index] = f"{prefix}{self.dragged_waypoint_index+1}"
                            
                            # Kullanıcıya bilgi ver
                            self.map_widget.update_status_message(f"Waypoint ismi '{current_name}' -> '{self.waypoint_names[self.dragged_waypoint_index]}' olarak değiştirildi")
            
            # Sürükleme durumunu sıfırla
            self.dragging_waypoint = False
            self.dragged_waypoint_index = None
            self.map_widget.setCursor(Qt.CrossCursor)
        elif self.map_widget.is_panning and event.button() == Qt.MiddleButton:
            self.map_widget.is_panning = False
            self.map_widget.setCursor(Qt.CrossCursor)
            
    def paint_route(self, painter):
        """Paint the current route being drawn"""
        if self.route_drawing_mode and self.current_route_points:
            # Draw the path
            painter.setPen(QPen(QColor(0, 120, 255), 2, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)  # Kesinlikle içini doldurmamak için
            
            # Draw lines between points
            for i in range(len(self.current_route_points) - 1):
                start_point = self.map_widget.geo_to_screen(*self.current_route_points[i])
                end_point = self.map_widget.geo_to_screen(*self.current_route_points[i + 1])
                painter.drawLine(start_point, end_point)
                
            # Snap göstergelerini çiz - route çiziminin üstünde görünsün
            if self.route_drawing_mode:
                self.snap_manager.paint_snap_indicators(painter)
                
                # En son iki nokta arasındaki mesafeyi hesapla ve yazdır (eğer en az 2 nokta varsa)
                if len(self.current_route_points) >= 2:
                    from utils import calculate_distance, calculate_bearing
                    last_index = len(self.current_route_points) - 1
                    lat1, lon1 = self.current_route_points[last_index - 1]
                    lat2, lon2 = self.current_route_points[last_index]
                    distance = calculate_distance(lat1, lon1, lat2, lon2)
                    track_angle = calculate_bearing(lat1, lon1, lat2, lon2)
                    
                    # Son iki noktanın ekran konumları
                    start_point = self.map_widget.geo_to_screen(*self.current_route_points[last_index - 1])
                    end_point = self.map_widget.geo_to_screen(*self.current_route_points[last_index])
                    
                    # Çizginin orta noktası
                    mid_x = (start_point.x() + end_point.x()) / 2
                    mid_y = (start_point.y() + end_point.y()) / 2
                    
                    # Çizginin açısını hesapla
                    dx = end_point.x() - start_point.x()
                    dy = end_point.y() - start_point.y()
                    line_angle = math.degrees(math.atan2(dy, dx))
                    
                    # Mesafe ve track angle bilgilerini ayrı ayrı formatla
                    distance_text = f"<{distance:.1f}>"
                    track_angle_text = f"{track_angle:.1f}°"
                    
                    # Özel font ayarları
                    old_font = painter.font()
                    font = painter.font()
                    font.setPointSize(9)  # Font boyutunu küçült
                    font.setBold(True)    # Kalın font
                    painter.setFont(font)
                    
                    # Metinlerin boyutlarını hesapla
                    angle_rect = painter.fontMetrics().boundingRect(track_angle_text)
                    dist_rect = painter.fontMetrics().boundingRect(distance_text)
                    
                    # Çizgiye dik olan yönü hesapla (90 derece ekle)
                    perpendicular_angle = math.radians(line_angle + 90)
                    offset = 10  # Çizgiden uzaklık (piksel cinsinden) - Daha yakın yerleşim
                    
                    # Açı metnini çizgiye paralel olarak çiz
                    painter.setPen(QPen(QColor(0, 0, 0), 1))
                    
                    # Açı metni için pozisyon ve döndürme
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
                    
                    # Mesafe metni için ters yön (çizginin diğer tarafı)
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
                    
                    # Mesafe metni için de aynı döndürme açısını kullan
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
                    
                    # Orijinal font ayarlarını geri yükle
                    painter.setFont(old_font)
                
                # Çizim için kalem rengini geri ayarla
                painter.setPen(QPen(QColor(0, 120, 255), 2, Qt.SolidLine))
            
            # Fare konumuna göre hayali çizgi ve potansiyel mesafe
            if self.mouse_position and len(self.current_route_points) > 0:
                # Son waypoint'ten fare konumuna çizgi çiz
                last_point = self.map_widget.geo_to_screen(*self.current_route_points[-1])
                
                # Hayali çizgiyi kesik çizgili stille çiz
                dash_pen = QPen(QColor(0, 120, 255), 1.5, Qt.DashLine)
                dash_pen.setDashPattern([5, 5])  # 5px çizgi, 5px boşluk
                painter.setPen(dash_pen)
                painter.drawLine(last_point, self.mouse_position)
                
                # Potansiyel mesafeyi hesapla
                last_lat, last_lon = self.current_route_points[-1]
                mouse_lat, mouse_lon = self.map_widget.screen_to_geo(self.mouse_position.x(), self.mouse_position.y())
                
                from utils import calculate_distance, calculate_bearing
                potential_distance = calculate_distance(last_lat, last_lon, mouse_lat, mouse_lon)
                track_angle = calculate_bearing(last_lat, last_lon, mouse_lat, mouse_lon)
                
                # Mesafe ve track angle bilgilerini ayrı ayrı formatla
                distance_text = f"<{potential_distance:.1f}>"
                track_angle_text = f"{track_angle:.1f}°"
                
                # Çizginin orta noktası
                mid_x = (last_point.x() + self.mouse_position.x()) / 2
                mid_y = (last_point.y() + self.mouse_position.y()) / 2
                
                # Çizginin açısını hesapla
                dx = self.mouse_position.x() - last_point.x()
                dy = self.mouse_position.y() - last_point.y()
                line_angle = math.degrees(math.atan2(dy, dx))
                
                # Özel font ayarları
                old_font = painter.font()
                font = painter.font()
                font.setPointSize(9)  # Font boyutunu küçült
                font.setBold(True)    # Kalın font
                painter.setFont(font)
                
                # Metinlerin boyutlarını hesapla
                angle_rect = painter.fontMetrics().boundingRect(track_angle_text)
                dist_rect = painter.fontMetrics().boundingRect(distance_text)
                
                # Çizgiye dik olan yönü hesapla (90 derece ekle)
                perpendicular_angle = math.radians(line_angle + 90)
                offset = 10  # Çizgiden uzaklık (piksel cinsinden) - Daha yakın yerleşim
                
                # Açı metnini çizgiye paralel olarak çiz
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                
                # Açı metni için pozisyon ve döndürme
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
                
                # Mesafe metni için ters yön (çizginin diğer tarafı)
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
                
                # Orijinal font ayarlarını geri yükle
                painter.setFont(old_font)
                
                # Çizim için kalem rengini geri ayarla
                painter.setPen(QPen(QColor(0, 120, 255), 2, Qt.SolidLine))
            
            # Draw points with their names
            painter.setBrush(QBrush(QColor(0, 120, 255)))
            for i, (lat, lon) in enumerate(self.current_route_points):
                point = self.map_widget.geo_to_screen(lat, lon)
                painter.drawEllipse(point, 2, 2)
                
                # Waypoint ismini yazdır
                if hasattr(self, 'waypoint_names') and len(self.waypoint_names) > i:
                    wp_name = self.waypoint_names[i]
                else:
                    wp_name = f"WP{i+1}"
                
                # Özel font ayarlarını kaydet
                old_font = painter.font()
                font = painter.font()
                font.setPointSize(8)  # Font boyutunu küçült
                font.setBold(True)    # Kalın font
                painter.setFont(font)
                
                # Noktanın biraz üstünde ismi göster - yeni font ile ölçü al
                text_rect = painter.fontMetrics().boundingRect(wp_name)
                bg_rect = QRectF(point.x() - text_rect.width()/2 - 2, 
                                 point.y() - text_rect.height() - 8,
                                 text_rect.width() + 4, 
                                 text_rect.height() + 2)
                
                # İsmi yaz - özel font ile (arka plan olmadan direkt)
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawText(QPointF(point.x() - text_rect.width()/2, 
                                        point.y() - text_rect.height() + 4), wp_name)
                
                # Orijinal font ayarlarını geri yükle
                painter.setFont(old_font)
                
                # Çizim için fırçayı geri ayarla
                painter.setBrush(QBrush(QColor(0, 120, 255)))
    
    def _get_waypoint_name_if_snapped(self, lat, lon):
        """
        Snap edilen nokta bir waypoint ise, waypoint adını döndürür.
        Eğer waypoint değilse None döndürür.
        """
        if not hasattr(self.map_widget, 'data_manager') or not hasattr(self.map_widget.data_manager, 'waypoint_coords'):
            return None
            
        # Waypoint koordinatlarını al
        waypoint_coords = self.map_widget.data_manager.waypoint_coords
        
        # Tüm waypoint'leri kontrol et (tam eşleşme için)
        for name, coords in waypoint_coords.items():
            # Koordinat hassasiyeti için çok küçük bir tolerans kullan
            w_lat, w_lon = coords
            # Hassas koordinat karşılaştırması (6 ondalık basamak)
            if abs(w_lat - lat) < 0.000001 and abs(w_lon - lon) < 0.000001:
                return name
                
        return None

    def _update_waypoint_names(self):
        """
        Rota çizimi sırasında ve sonrasında waypoint isimlerini günceller.
        Eğer nokta bir waypoint'e snap edildiyse onun gerçek adını, değilse WP1, WP2 gibi varsayılan adları kullanır.
        """
        # Eğer waypoint_names listesi daha önce oluşturulmadıysa veya boşsa
        if not hasattr(self, 'waypoint_names') or self.waypoint_names is None:
            self.waypoint_names = []
            
        # Nokta sayısı değiştiyse listeyi güncelle
        current_points_count = len(self.current_route_points)
        current_names_count = len(self.waypoint_names)
        
        if current_names_count > current_points_count:
            # Fazla isimleri sil
            self.waypoint_names = self.waypoint_names[:current_points_count]
        elif current_names_count < current_points_count:
            # Eksik isimler için varsayılan isimler ekle
            for i in range(current_names_count, current_points_count):
                # Her yeni nokta için varsayılan waypoint ismi ekle
                self.waypoint_names.append(f"WP{i+1}")
                
        # Noktalara gerçek waypoint isimlerini atama kontrolü
        # Her nokta için koordinatları kontrol et ve waypoint'e denk gelenler için isim güncelle
        for i, (lat, lon) in enumerate(self.current_route_points):
            # Nokta bir waypoint'e denk geliyor mu kontrol et
            waypoint_name = self._get_waypoint_name_if_snapped(lat, lon)
            
            if waypoint_name:
                # Waypoint'e snap olmuş noktaya XML'deki waypoint adını ata
                self.waypoint_names[i] = waypoint_name
            elif self.waypoint_names[i] != "":
                # Mevcut ismin waypoint_coords'ta olup olmadığını kontrol et
                is_real_waypoint = False
                if hasattr(self.map_widget, 'data_manager') and hasattr(self.map_widget.data_manager, 'waypoint_coords'):
                    is_real_waypoint = self.waypoint_names[i] in self.map_widget.data_manager.waypoint_coords
                
                # Varsayılan prefix'i her durumda tanımla
                prefix = "WP"  # Varsayılan prefix
                
                # Eğer şu anki isim bir waypoint adı ise (gerçekten waypoint_coords'ta varsa) 
                # ama nokta artık bir waypoint'e denk gelmiyorsa, varsayılan isme döndür
                if is_real_waypoint and not waypoint_name:
                    # Rota türüne göre prefix belirle (pointmerge, trombone vb.)
                    for route in self.map_widget.drawn_elements.get('routes', []):
                        if 'points' in route and self.current_route_points == route['points']:
                            if 'pointmerge' in route.get('id', ''):
                                prefix = "PM"
                                break
                            elif 'trombone' in route.get('id', ''):
                                prefix = "T"
                                break
                    
                    # Varsayılan isme döndür
                    self.waypoint_names[i] = f"{prefix}{i+1}"
                    
                    # Kullanıcıya bilgi ver 
                    self.map_widget.update_status_message(f"Waypoint ismi orijinal formata döndürüldü: {self.waypoint_names[i]}")
                # İsim bir waypoint adı değilse, herhangi bir değişiklik yapma
            elif self.waypoint_names[i] == "":
                # Eğer isim boş ise varsayılan olarak bir isim ver
                prefix = "WP"  # Varsayılan prefix
                
                # Rota türüne göre prefix'i belirle
                for route in self.map_widget.drawn_elements.get('routes', []):
                    if 'points' in route and self.current_route_points == route['points']:
                        if 'pointmerge' in route.get('id', ''):
                            prefix = "PM"
                            break
                        elif 'trombone' in route.get('id', ''):
                            prefix = "T"
                            break
                
                self.waypoint_names[i] = f"{prefix}{i+1}"