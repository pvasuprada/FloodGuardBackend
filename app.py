"""
FloodGuard Backend API
Main Flask application with 4 API endpoints
"""
from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS
from data_service import DataService
import os

app = Flask(__name__)
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


@app.route('/api/reported-floods', methods=['GET', 'OPTIONS'])
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


@app.route('/api/reported-floods', methods=['POST', 'OPTIONS'])
def post_reported_flood():
    """API Endpoint 4: Post values to Reported Floods to AWS or local file"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if not data_service:
            return jsonify({"error": "Data service not initialized"}), 500
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = data_service.post_reported_flood(data)
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

