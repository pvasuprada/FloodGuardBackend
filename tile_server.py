"""
FloodGuard Tile Server
Serves flood risk data as map tiles in XYZ format (compatible with OpenLayers)
"""
from flask import Flask, Response, send_file
from flask_cors import CORS
from data_service import DataService
import geopandas as gpd
from shapely.geometry import box
from PIL import Image, ImageDraw
import io
import math
import os

app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize data service
try:
    data_service = DataService()
except Exception as e:
    print(f"Warning: Error initializing data service: {e}")
    data_service = None

# Cache for GeoDataFrame (to avoid reloading on every request)
_gdf_cache = None
_cache_path = None


def load_geojson_to_gdf():
    """Load GeoJSON data into a GeoDataFrame, with caching"""
    global _gdf_cache, _cache_path
    
    if data_service is None:
        return None
    
    # Determine the path to use
    if data_service.data_source == 'local':
        local_config = data_service.config.get('local', {})
        geojson_path = local_config.get('geojson_path', 'sample_data/floodrisk.geojson')
    else:
        # For AWS, we'd need to download first - for now, return None
        # You could implement AWS download logic here
        return None
    
    # Check if path changed or cache is empty
    if _gdf_cache is None or _cache_path != geojson_path:
        try:
            if os.path.exists(geojson_path):
                # Read GeoJSON file using geopandas
                _gdf_cache = gpd.read_file(geojson_path)
                _cache_path = geojson_path
                print(f"Loaded GeoJSON from {geojson_path} with {len(_gdf_cache)} features")
            else:
                print(f"GeoJSON file not found: {geojson_path}")
                return None
        except Exception as e:
            print(f"Error loading GeoJSON: {e}")
            return None
    
    return _gdf_cache


def tile_to_bbox_mercator(z, x, y):
    """
    Convert tile coordinates (z, x, y) to bounding box in Web Mercator (EPSG:3857)
    Returns bbox in meters (Web Mercator coordinates)
    """
    # Web Mercator bounds in meters
    EARTH_RADIUS = 6378137.0
    MAX_EXTENT = 20037508.342789244
    
    n = 2.0 ** z
    minx = (x / n) * 2 * MAX_EXTENT - MAX_EXTENT
    maxx = ((x + 1) / n) * 2 * MAX_EXTENT - MAX_EXTENT
    
    miny = MAX_EXTENT - ((y + 1) / n) * 2 * MAX_EXTENT
    maxy = MAX_EXTENT - (y / n) * 2 * MAX_EXTENT
    
    return (minx, miny, maxx, maxy)


def tile_to_bbox_wgs84(z, x, y):
    """
    Convert tile coordinates (z, x, y) to bounding box in WGS84 (EPSG:4326)
    Returns bbox in degrees (lat/lon)
    """
    n = 2.0 ** z
    minx = x / n * 360.0 - 180.0
    maxx = (x + 1) / n * 360.0 - 180.0
    
    miny_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    maxy_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    
    miny = math.degrees(miny_rad)
    maxy = math.degrees(maxy_rad)
    
    return (minx, miny, maxx, maxy)


def get_severity_color(severity):
    """Get color based on severity level"""
    severity_lower = str(severity).lower() if severity else 'low'
    
    color_map = {
        'high': (255, 0, 0, 180),      # Red with transparency
        'medium': (255, 165, 0, 150),  # Orange with transparency
        'low': (255, 255, 0, 120),     # Yellow with transparency
        'critical': (128, 0, 128, 200), # Purple with transparency
    }
    
    return color_map.get(severity_lower, (200, 200, 200, 100))  # Default gray


def render_tile(z, x, y, tile_size=256):
    """
    Render a map tile as PNG image using Web Mercator (EPSG:3857) projection
    Input GeoJSON is expected to be in EPSG:4326, will be reprojected to EPSG:3857
    """
    # Get tile bounding box in Web Mercator (EPSG:3857) - meters
    bbox_mercator = tile_to_bbox_mercator(z, x, y)
    tile_bbox_mercator = box(*bbox_mercator)
    
    # Load GeoDataFrame
    gdf = load_geojson_to_gdf()
    if gdf is None or len(gdf) == 0:
        # Return transparent tile if no data
        img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
        return img
    
    # Ensure CRS is WGS84 (EPSG:4326) - GeoJSON standard
    if gdf.crs is None:
        gdf.set_crs('EPSG:4326', inplace=True)
    elif str(gdf.crs) != 'EPSG:4326':
        # Convert to WGS84 if not already
        if str(gdf.crs) != 'EPSG:3857':
            gdf = gdf.to_crs('EPSG:4326')
    
    # Reproject to Web Mercator (EPSG:3857) for rendering
    # This is the standard projection for web tiles
    gdf_mercator = gdf.to_crs('EPSG:3857')
    
    # Filter features that intersect with tile bounding box (in Web Mercator)
    try:
        intersecting = gdf_mercator[gdf_mercator.intersects(tile_bbox_mercator)]
    except Exception as e:
        print(f"Error filtering features: {e}")
        intersecting = gdf_mercator
    
    if len(intersecting) == 0:
        # Return transparent tile if no features intersect
        img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
        return img
    
    # Create image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Coordinate transformation functions (Web Mercator coordinates in meters)
    minx, miny, maxx, maxy = bbox_mercator
    width = maxx - minx
    height = maxy - miny
    
    def merc_x_to_pixel(x_coord):
        """Convert Web Mercator X coordinate to pixel X"""
        return int((x_coord - minx) / width * tile_size)
    
    def merc_y_to_pixel(y_coord):
        """Convert Web Mercator Y coordinate to pixel Y (flip Y axis)"""
        return int((maxy - y_coord) / height * tile_size)
    
    # Draw each feature (geometries are now in Web Mercator EPSG:3857)
    for idx, row in intersecting.iterrows():
        geom = row.geometry
        
        # Get color from properties
        severity = row.get('severity', row.get('severity_level', 'low'))
        color = get_severity_color(severity)
        
        # Handle different geometry types
        if geom.geom_type == 'Polygon':
            # Extract exterior coordinates (in Web Mercator meters)
            coords = list(geom.exterior.coords)
            points = [(merc_x_to_pixel(x_coord), merc_y_to_pixel(y_coord)) for x_coord, y_coord in coords]
            
            # Draw filled polygon
            if len(points) > 2:
                draw.polygon(points, fill=color, outline=(0, 0, 0, 255), width=1)
            
            # Draw interior holes
            for interior in geom.interiors:
                interior_coords = list(interior.coords)
                interior_points = [(merc_x_to_pixel(x_coord), merc_y_to_pixel(y_coord)) 
                                  for x_coord, y_coord in interior_coords]
                if len(interior_points) > 2:
                    draw.polygon(interior_points, fill=(0, 0, 0, 0), outline=(0, 0, 0, 255), width=1)
        
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                coords = list(poly.exterior.coords)
                points = [(merc_x_to_pixel(x_coord), merc_y_to_pixel(y_coord)) 
                          for x_coord, y_coord in coords]
                
                if len(points) > 2:
                    draw.polygon(points, fill=color, outline=(0, 0, 0, 255), width=1)
                
                for interior in poly.interiors:
                    interior_coords = list(interior.coords)
                    interior_points = [(merc_x_to_pixel(x_coord), merc_y_to_pixel(y_coord)) 
                                      for x_coord, y_coord in interior_coords]
                    if len(interior_points) > 2:
                        draw.polygon(interior_points, fill=(0, 0, 0, 0), outline=(0, 0, 0, 255), width=1)
        
        elif geom.geom_type in ['Point', 'MultiPoint']:
            # For points, draw a small circle
            if geom.geom_type == 'Point':
                points = [geom]
            else:
                points = list(geom.geoms)
            
            for point in points:
                px = merc_x_to_pixel(point.x)
                py = merc_y_to_pixel(point.y)
                radius = 3
                draw.ellipse([px - radius, py - radius, px + radius, py + radius], 
                           fill=color, outline=(0, 0, 0, 255))
        
        elif geom.geom_type in ['LineString', 'MultiLineString']:
            # For lines, draw the path
            if geom.geom_type == 'LineString':
                lines = [geom]
            else:
                lines = list(geom.geoms)
            
            for line in lines:
                coords = list(line.coords)
                points = [(merc_x_to_pixel(x_coord), merc_y_to_pixel(y_coord)) 
                         for x_coord, y_coord in coords]
                if len(points) > 1:
                    draw.line(points, fill=color, width=2)
    
    return img


@app.route('/<int:z>/<int:x>/<int:y>', methods=['GET'])
def get_tile(z, x, y):
    """
    Serve map tile in XYZ format using Web Mercator (EPSG:3857) projection
    Compatible with OpenLayers and other mapping libraries
    
    URL format: /{z}/{x}/{y}
    - z: zoom level (0-20)
    - x: tile X coordinate
    - y: tile Y coordinate
    
    Input GeoJSON data is expected in EPSG:4326 (WGS84) and will be
    automatically reprojected to EPSG:3857 (Web Mercator) for rendering.
    """
    try:
        # Validate tile coordinates
        if z < 0 or z > 20:
            return Response("Invalid zoom level", status=400, mimetype='text/plain')
        
        max_tile = 2 ** z
        if x < 0 or x >= max_tile or y < 0 or y >= max_tile:
            return Response("Invalid tile coordinates", status=400, mimetype='text/plain')
        
        # Render tile
        img = render_tile(z, x, y)
        
        # Convert to PNG bytes
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # Return PNG image
        return Response(
            img_io.getvalue(),
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Content-Type': 'image/png'
            }
        )
    
    except Exception as e:
        print(f"Error rendering tile {z}/{x}/{y}: {e}")
        # Return transparent tile on error
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        return Response(
            img_io.getvalue(),
            mimetype='image/png'
        )


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    gdf = load_geojson_to_gdf()
    return {
        "status": "healthy",
        "data_loaded": gdf is not None and len(gdf) > 0 if gdf is not None else False,
        "feature_count": len(gdf) if gdf is not None else 0
    }, 200


if __name__ == '__main__':
    print("Starting FloodGuard Tile Server...")
    print("Projection: Web Mercator (EPSG:3857)")
    print("Input data: EPSG:4326 (WGS84) - auto-reprojected to EPSG:3857")
    print("Tile endpoint: http://localhost:3002/{z}/{x}/{y}")
    print("Example: http://localhost:3002/10/512/512")
    app.run(debug=True, host='0.0.0.0', port=3002)

