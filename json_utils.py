import json
from PyQt5.QtGui import QColor

class QColorJSONEncoder(json.JSONEncoder):
    """QColor nesnelerini JSON-serileştirilebilir formata dönüştüren özel JSON kodlayıcı"""
    def default(self, obj):
        if isinstance(obj, QColor):
            # QColor nesnesini rgba değerleri olarak serileştir
            return {
                "_qcolor_": True,
                "r": obj.red(),
                "g": obj.green(),
                "b": obj.blue(),
                "a": obj.alpha()
            }
        # Diğer nesne tipleri için default encoder'ı kullan
        return super().default(obj)

def decode_qcolor(obj):
    """JSON'dan QColor nesnelerini geri çözen yardımcı fonksiyon"""
    if "_qcolor_" in obj:
        # QColor nesnesini oluştur
        return QColor(obj["r"], obj["g"], obj["b"], obj["a"])
    return obj

def json_loads(json_str):
    """JSON string'inden QColor nesnelerini doğru şekilde çözümleyen fonksiyon"""
    return json.loads(json_str, object_hook=decode_qcolor)

def json_dumps(obj, indent=None):
    """QColor nesnelerini içeren objeleri JSON string'ine çeviren fonksiyon"""
    return json.dumps(obj, cls=QColorJSONEncoder, indent=indent)
