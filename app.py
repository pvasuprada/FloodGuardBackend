"""
FloodGuard Backend API
Main Flask application with 4 API endpoints
"""
from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS
from data_service import DataService
import os
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Enable CORS for all routes with permissive settings
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    },
    r"/health": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    }
})

# Initialize data service
try:
    data_service = DataService()
except Exception as e:
    print(f"Warning: Error initializing data service: {e}")
    data_service = None


@app.route('/api/floodrisk', methods=['GET', 'OPTIONS'])
def get_floodrisk():
    """API Endpoint 1: Fetch Flood Risk GeoJSON from AWS Server or local file"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        
        # For local mode with large files, stream directly from file
        if data_service.data_source == 'local':
            local_config = data_service.config.get('local', {})
            geojson_path = local_config.get('geojson_path', 'sample_data/floodrisk.geojson')
            
            # Check if file exists and get its size
            if os.path.exists(geojson_path):
                file_size = os.path.getsize(geojson_path)
                
                # For large files (>10MB), stream directly using send_file
                if file_size > 10 * 1024 * 1024:  # > 10MB
                    # Use send_file which handles streaming automatically
                    return send_file(
                        geojson_path,
                        mimetype='application/json',
                        as_attachment=False,
                        conditional=True  # Supports range requests
                    )
                else:
                    # For smaller files, use normal method
                    geojson_data = data_service.fetch_geojson()
                    if geojson_data:
                        return jsonify(geojson_data), 200
                    else:
                        return jsonify({"error": "Failed to fetch GeoJSON data"}), 500
            else:
                return jsonify({"error": "GeoJSON file not found"}), 404
        else:
            # AWS mode - use normal method
            geojson_data = data_service.fetch_geojson()
            if geojson_data:
                return jsonify(geojson_data), 200
            else:
                return jsonify({"error": "Failed to fetch GeoJSON data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reported-floods-geojsonlayer', methods=['GET', 'OPTIONS'])
def get_reported_floods():
    """API Endpoint 2: Fetch values from Reported Floods table and create GeoJSON"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        geojson_data = data_service.fetch_reported_floods()
        if geojson_data:
            return jsonify(geojson_data), 200
        else:
            return jsonify({"error": "Failed to fetch reported floods data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reported-floods-geojsonlayer/hyderabad', methods=['GET', 'OPTIONS'])
def get_reported_floods_hyderabad():
    """API Endpoint: Fetch all reported floods as GeoJSON"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        geojson_data = data_service.fetch_reported_floods()
        if geojson_data:
            return jsonify(geojson_data), 200
        else:
            return jsonify({"error": "Failed to fetch reported floods data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reported-floods', methods=['GET', 'OPTIONS'])
def get_reported_floods_structured():
    """API Endpoint: Fetch all reported floods as structured array (for UI display)"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        reports = data_service.fetch_reported_floods_structured()
        if reports is not None:
            return jsonify(reports), 200
        else:
            return jsonify({"error": "Failed to fetch reported floods data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rain-gauge', methods=['GET', 'OPTIONS'])
def get_rain_gauge():
    """API Endpoint 3: Fetch values from AWS Server for rain gauge and create GeoJSON"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        geojson_data = data_service.fetch_rain_gauge()
        if geojson_data:
            return jsonify(geojson_data), 200
        else:
            return jsonify({"error": "Failed to fetch rain gauge data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/report-flood', methods=['POST', 'OPTIONS'])
def post_reported_flood():
    """API Endpoint 4: Post values to Reported Floods to AWS or local file
    
    Accepts form data with:
    - location (required): Location name (e.g., "Banjara Hills")
    - severity_level (required): Severity level (e.g., "low", "medium", "high")
    - description (optional): Description text (max 500 characters)
    - your_name (optional): Reporter name
    - photo_evidence (optional): Image file (PNG, JPG up to 10MB)
    - latitude (optional): Latitude coordinate
    - longitude (optional): Longitude coordinate
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        
        # Get form data
        location = request.form.get('location')
        severity_level = request.form.get('severity_level')
        description = request.form.get('description', '')
        your_name = request.form.get('your_name', '')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        # Validate required fields
        if not location:
            return jsonify({"error": "Location is required"}), 400
        if not severity_level:
            return jsonify({"error": "Severity level is required"}), 400
        
        # Validate description length
        if description and len(description) > 500:
            return jsonify({"error": "Description must be 500 characters or less"}), 400
        
        # Handle file upload
        photo_url = None
        if 'photo_evidence' in request.files:
            file = request.files['photo_evidence']
            if file and file.filename and allowed_file(file.filename):
                # Check file size
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    return jsonify({"error": "File size exceeds 10MB limit"}), 400
                
                # Save file
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                photo_url = f"/uploads/{unique_filename}"
        
        # Get coordinates - use provided or default to None
        # In production, you might want to geocode the location name
        lat = float(latitude) if latitude else None
        lon = float(longitude) if longitude else None
        
        # If no coordinates provided, use default (0,0) or handle error
        if lat is None or lon is None:
            # You might want to geocode the location name here
            # For now, we'll use None and let the frontend handle it
            lat = 0.0
            lon = 0.0
        
        # Create GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "id": str(uuid.uuid4()),
                "location": location,
                "severity": severity_level.lower(),
                "description": description,
                "reported_by": your_name if your_name else "Anonymous",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "active",
                "photo_url": photo_url
            }
        }
        
        result = data_service.post_reported_flood(feature)
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 500
    except ValueError as e:
        return jsonify({"error": f"Invalid coordinate values: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<filename>', methods=['GET'])
def serve_upload(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))


@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        "status": "healthy",
        "data_source": data_service.data_source if data_service else "unknown"
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3001)

