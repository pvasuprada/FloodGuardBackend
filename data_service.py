"""
Data service module for handling PostgreSQL, AWS, and local data sources
"""
import yaml
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from datetime import datetime


class DataService:
    def __init__(self, config_path='config.yaml'):
        """Initialize data service with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.data_source = self.config.get('data_source', 'local')
        
        if self.data_source == 'AWS':
            self._init_aws_clients()
        elif self.data_source == 'postgresql':
            self._init_postgresql_pool()
    
    def _init_aws_clients(self):
        """Initialize AWS clients"""
        aws_config = self.config.get('aws', {})
        self.s3_client = boto3.client(
            's3',
            region_name=aws_config.get('region'),
            aws_access_key_id=aws_config.get('access_key_id'),
            aws_secret_access_key=aws_config.get('secret_access_key')
        )
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=aws_config.get('region'),
            aws_access_key_id=aws_config.get('access_key_id'),
            aws_secret_access_key=aws_config.get('secret_access_key')
        )
        self.s3_bucket = aws_config.get('s3_bucket')
        self.dynamodb_table_reported_floods = aws_config.get('dynamodb_table_reported_floods')
        self.dynamodb_table_rain_gauge = aws_config.get('dynamodb_table_rain_gauge')
        self.s3_geojson_key = aws_config.get('s3_geojson_key')
    
    def _init_postgresql_pool(self):
        """Initialize PostgreSQL connection pool"""
        pg_config = self.config.get('postgresql', {})
        try:
            self.pg_pool = SimpleConnectionPool(
                minconn=pg_config.get('min_connections', 1),
                maxconn=pg_config.get('max_connections', 10),
                host=pg_config.get('host', 'localhost'),
                port=pg_config.get('port', 5432),
                database=pg_config.get('database', 'FloodGuard'),
                user=pg_config.get('user', 'postgres'),
                password=pg_config.get('password', 'postgres')
            )
            if self.pg_pool:
                print("PostgreSQL connection pool created successfully")
        except Exception as e:
            print(f"Error creating PostgreSQL connection pool: {e}")
            self.pg_pool = None
    
    def _get_pg_connection(self):
        """Get a connection from the pool"""
        if not self.pg_pool:
            raise Exception("PostgreSQL connection pool not initialized")
        return self.pg_pool.getconn()
    
    def _return_pg_connection(self, conn):
        """Return a connection to the pool"""
        if self.pg_pool:
            self.pg_pool.putconn(conn)
    
    def fetch_geojson(self):
        """Fetch GeoJSON from AWS S3 or local file (API #1 - unchanged)"""
        if self.data_source == 'AWS':
            try:
                response = self.s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=self.s3_geojson_key
                )
                geojson_data = json.loads(response['Body'].read().decode('utf-8'))
                return geojson_data
            except ClientError as e:
                print(f"Error fetching from S3: {e}")
                return None
        else:
            # Local mode - always read from local file for API #1
            local_config = self.config.get('local', {})
            geojson_path = local_config.get('geojson_path', 'sample_data/floodrisk.geojson')
            try:
                with open(geojson_path, 'r') as f:
                    geojson_data = json.load(f)
                return geojson_data
            except FileNotFoundError:
                print(f"Error: GeoJSON file not found at {geojson_path}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in GeoJSON file: {e}")
                return None
            except Exception as e:
                print(f"Error reading local GeoJSON: {e}")
                return None
    
    def fetch_reported_floods(self):
        """Fetch reported floods from PostgreSQL and convert to GeoJSON"""
        if self.data_source == 'postgresql':
            conn = None
            try:
                conn = self._get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Query with PostGIS ST_AsGeoJSON to convert geometry to GeoJSON
                query = """
                    SELECT 
                        id,
                        location,
                        severity,
                        COALESCE(category, 'Flooding') as category,
                        description,
                        reported_by,
                        confidence,
                        timestamp,
                        verified,
                        status,
                        photo_url,
                        ST_AsGeoJSON(geom)::json as geometry
                    FROM reported_floods
                    ORDER BY timestamp DESC
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                features = []
                for row in rows:
                    # Parse the geometry JSON
                    geom_json = row['geometry']
                    
                    feature = {
                        "type": "Feature",
                        "geometry": geom_json,
                        "properties": {
                            "id": str(row['id']),
                            "location": row['location'],
                            "severity": row['severity'].lower() if row['severity'] else 'low',
                            "category": row['category'],
                            "description": row['description'] or '',
                            "reported_by": row['reported_by'] or 'Anonymous',
                            "confidence": row['confidence'] or 0,
                            "timestamp": row['timestamp'].isoformat() + "Z" if row['timestamp'] else '',
                            "verified": row['verified'] or False,
                            "status": row['status'] or 'active',
                            "photo_url": row['photo_url'] or None
                        }
                    }
                    features.append(feature)
                
                geojson = {
                    "type": "FeatureCollection",
                    "features": features
                }
                cursor.close()
                return geojson
            except Exception as e:
                print(f"Error fetching reported floods from PostgreSQL: {e}")
                return None
            finally:
                if conn:
                    self._return_pg_connection(conn)
        elif self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                response = table.scan()
                items = response.get('Items', [])
                
                features = []
                for item in items:
                    lat = float(item.get('latitude') or item.get('lat') or item.get('coordinates', {}).get('lat', 0))
                    lng = float(item.get('longitude') or item.get('lng') or item.get('coordinates', {}).get('lng', 0))
                    
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "properties": {
                            k: v for k, v in item.items() 
                            if k not in ['latitude', 'longitude', 'lat', 'lng', 'coordinates']
                        }
                    }
                    features.append(feature)
                
                geojson = {
                    "type": "FeatureCollection",
                    "features": features
                }
                return geojson
            except ClientError as e:
                print(f"Error fetching from DynamoDB: {e}")
                return None
        else:
            # Local mode - read from sample data JSON
            local_config = self.config.get('local', {})
            floods_path = local_config.get('reported_floods_path', 'sample_data/reported_floods.json')
            try:
                with open(floods_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
                    return data
                elif isinstance(data, list):
                    features = []
                    for report in data:
                        feature = self._convert_flood_report_to_geojson(report)
                        features.append(feature)
                    
                    geojson = {
                        "type": "FeatureCollection",
                        "features": features
                    }
                    return geojson
                else:
                    return None
            except Exception as e:
                print(f"Error reading local reported floods: {e}")
                return None
    
    def fetch_reported_floods_structured(self):
        """Fetch reported floods as structured array format (for UI display)"""
        if self.data_source == 'postgresql':
            conn = None
            try:
                conn = self._get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                query = """
                    SELECT 
                        id,
                        location,
                        severity,
                        COALESCE(category, 'Flooding') as category,
                        description,
                        reported_by,
                        confidence,
                        timestamp,
                        verified,
                        photo_url,
                        ST_Y(geom) as lat,
                        ST_X(geom) as lng
                    FROM reported_floods
                    ORDER BY timestamp DESC
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                reports = []
                for row in rows:
                    report = {
                        "id": str(row['id']),
                        "location": row['location'],
                        "severity": row['severity'].capitalize() if row['severity'] else 'Low',
                        "category": row['category'],
                        "description": row['description'] or '',
                        "reporter": row['reported_by'] or 'Anonymous',
                        "confidence": row['confidence'] or 0,
                        "timestamp": row['timestamp'].isoformat() + "Z" if row['timestamp'] else '',
                        "verified": row['verified'] or False,
                        "coordinates": {
                            "lat": float(row['lat']) if row['lat'] else 0.0,
                            "lng": float(row['lng']) if row['lng'] else 0.0
                        }
                    }
                    
                    if row['photo_url']:
                        report['imageUrl'] = row['photo_url']
                    
                    reports.append(report)
                
                cursor.close()
                return reports
            except Exception as e:
                print(f"Error fetching reported floods from PostgreSQL: {e}")
                return None
            finally:
                if conn:
                    self._return_pg_connection(conn)
        elif self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                response = table.scan()
                items = response.get('Items', [])
                
                reports = []
                for item in items:
                    lat = float(item.get('latitude') or item.get('lat') or item.get('coordinates', {}).get('lat', 0))
                    lng = float(item.get('longitude') or item.get('lng') or item.get('coordinates', {}).get('lng', 0))
                    
                    report = {
                        "id": str(item.get('id', '')),
                        "location": str(item.get('location', '')),
                        "severity": str(item.get('severity', '')).capitalize(),
                        "category": str(item.get('category', 'Flooding')),
                        "description": str(item.get('description', '')),
                        "reporter": str(item.get('reported_by') or item.get('reporter', 'Anonymous')),
                        "confidence": int(item.get('confidence', 0)),
                        "timestamp": str(item.get('timestamp', '')),
                        "verified": bool(item.get('verified', False)),
                        "coordinates": {
                            "lat": lat,
                            "lng": lng
                        }
                    }
                    
                    if 'photo_url' in item or 'imageUrl' in item:
                        report['imageUrl'] = str(item.get('photo_url') or item.get('imageUrl', ''))
                    
                    reports.append(report)
                
                return reports
            except ClientError as e:
                print(f"Error fetching from DynamoDB: {e}")
                return None
        else:
            # Local mode
            local_config = self.config.get('local', {})
            floods_path = local_config.get('reported_floods_path', 'sample_data/reported_floods.json')
            try:
                with open(floods_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and data.get('type') == 'FeatureCollection':
                    reports = []
                    for feature in data.get('features', []):
                        props = feature.get('properties', {})
                        coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                        
                        report = {
                            "id": str(props.get('id', '')),
                            "location": str(props.get('location', '')),
                            "severity": str(props.get('severity', '')).capitalize(),
                            "category": str(props.get('category', 'Flooding')),
                            "description": str(props.get('description', '')),
                            "reporter": str(props.get('reported_by') or props.get('reporter', 'Anonymous')),
                            "confidence": int(props.get('confidence', 0)),
                            "timestamp": str(props.get('timestamp', '')),
                            "verified": bool(props.get('verified', False)),
                            "coordinates": {
                                "lat": float(coords[1]) if len(coords) > 1 else 0,
                                "lng": float(coords[0]) if len(coords) > 0 else 0
                            }
                        }
                        
                        if 'photo_url' in props:
                            report['imageUrl'] = str(props['photo_url'])
                        
                        reports.append(report)
                    
                    return reports
                else:
                    return None
            except Exception as e:
                print(f"Error reading local reported floods: {e}")
                return None
    
    def fetch_rain_gauge(self):
        """Fetch rain gauge data from PostgreSQL and convert to GeoJSON"""
        if self.data_source == 'postgresql':
            conn = None
            try:
                conn = self._get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                query = """
                    SELECT 
                        gauge_id,
                        name,
                        location,
                        mandal_name,
                        rainfall_mm,
                        temperature,
                        humidity,
                        date_time,
                        last_updated,
                        status,
                        ST_AsGeoJSON(geom)::json as geometry
                    FROM weather_stations
                    WHERE status = 'active'
                    ORDER BY last_updated DESC NULLS LAST, date_time DESC NULLS LAST
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                features = []
                for row in rows:
                    geom_json = row['geometry']
                    
                    feature = {
                        "type": "Feature",
                        "geometry": geom_json,
                        "properties": {
                            "gauge_id": str(row['gauge_id']),
                            "name": row['name'],
                            "location": row['location'],
                            "mandal_name": row['mandal_name'],
                            "rainfall_mm": float(row['rainfall_mm']) if row['rainfall_mm'] is not None else None,
                            "temperature": float(row['temperature']) if row['temperature'] is not None else None,
                            "humidity": float(row['humidity']) if row['humidity'] is not None else None,
                            "date_time": str(row['date_time']) if row['date_time'] else '',
                            "last_updated": row['last_updated'].isoformat() if row['last_updated'] else '',
                            "status": row['status'] or 'active'
                        }
                    }
                    features.append(feature)
                
                geojson = {
                    "type": "FeatureCollection",
                    "features": features
                }
                cursor.close()
                return geojson
            except Exception as e:
                print(f"Error fetching rain gauge data from PostgreSQL: {e}")
                return None
            finally:
                if conn:
                    self._return_pg_connection(conn)
        elif self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_rain_gauge)
                response = table.scan()
                items = response.get('Items', [])
                
                features = []
                for item in items:
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                float(item.get('longitude', 0)),
                                float(item.get('latitude', 0))
                            ]
                        },
                        "properties": {
                            k: v for k, v in item.items() 
                            if k not in ['latitude', 'longitude']
                        }
                    }
                    features.append(feature)
                
                geojson = {
                    "type": "FeatureCollection",
                    "features": features
                }
                return geojson
            except ClientError as e:
                print(f"Error fetching from DynamoDB: {e}")
                return None
        else:
            # Local mode
            local_config = self.config.get('local', {})
            rain_gauge_path = local_config.get('rain_gauge_path', 'sample_data/rain_gauge.geojson')
            try:
                with open(rain_gauge_path, 'r') as f:
                    geojson_data = json.load(f)
                return geojson_data
            except Exception as e:
                print(f"Error reading local rain gauge: {e}")
                return None
    
    def post_reported_flood(self, flood_data):
        """Post reported flood data to PostgreSQL"""
        if self.data_source == 'postgresql':
            conn = None
            try:
                conn = self._get_pg_connection()
                cursor = conn.cursor()
                
                # Extract data from GeoJSON feature
                props = flood_data.get('properties', {})
                geom = flood_data.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                if len(coords) < 2:
                    return {"status": "error", "message": "Invalid coordinates"}
                
                longitude = coords[0]
                latitude = coords[1]
                
                # Parse timestamp if provided as string
                timestamp = props.get('timestamp')
                if timestamp and isinstance(timestamp, str):
                    try:
                        # Remove 'Z' suffix and parse ISO format
                        timestamp_str = timestamp.replace('Z', '+00:00')
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except (ValueError, AttributeError):
                        # If parsing fails, use None to let database default handle it
                        timestamp = None
                
                # Insert into PostgreSQL using PostGIS ST_SetSRID and ST_MakePoint
                query = """
                    INSERT INTO reported_floods (
                        id, location, severity, category, description, 
                        reported_by, confidence, timestamp, verified, 
                        status, photo_url, geom
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    )
                """
                
                values = (
                    props.get('id'),
                    props.get('location'),
                    props.get('severity', 'low').lower(),
                    props.get('category', 'Flooding'),
                    props.get('description', ''),
                    props.get('reported_by', 'Anonymous'),
                    props.get('confidence', 0),
                    timestamp,  # Parsed datetime or None (will use database default)
                    props.get('verified', False),
                    props.get('status', 'active'),
                    props.get('photo_url'),
                    longitude,
                    latitude
                )
                
                cursor.execute(query, values)
                conn.commit()
                cursor.close()
                
                return {"status": "success", "message": "Flood data posted successfully"}
            except Exception as e:
                if conn:
                    conn.rollback()
                print(f"Error posting to PostgreSQL: {e}")
                return {"status": "error", "message": str(e)}
            finally:
                if conn:
                    self._return_pg_connection(conn)
        elif self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                
                if 'geometry' in flood_data:
                    coords = flood_data['geometry'].get('coordinates', [])
                    if len(coords) >= 2:
                        flood_data['longitude'] = coords[0]
                        flood_data['latitude'] = coords[1]
                
                dynamodb_item = self._convert_to_dynamodb_item(flood_data)
                response = table.put_item(Item=dynamodb_item)
                return {"status": "success", "message": "Flood data posted successfully"}
            except ClientError as e:
                print(f"Error posting to DynamoDB: {e}")
                return {"status": "error", "message": str(e)}
        else:
            # Local mode - append to local file
            local_config = self.config.get('local', {})
            floods_path = local_config.get('reported_floods_path', 'sample_data/reported_floods.json')
            try:
                if Path(floods_path).exists():
                    with open(floods_path, 'r') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = {"type": "FeatureCollection", "features": []}
                
                if isinstance(flood_data, dict):
                    if 'type' in flood_data and flood_data['type'] == 'Feature':
                        existing_data['features'].append(flood_data)
                    elif 'geometry' in flood_data and 'properties' in flood_data:
                        feature = {
                            "type": "Feature",
                            "geometry": flood_data['geometry'],
                            "properties": flood_data['properties']
                        }
                        existing_data['features'].append(feature)
                    else:
                        return {"status": "error", "message": "Invalid GeoJSON format"}
                    
                    with open(floods_path, 'w') as f:
                        json.dump(existing_data, f, indent=2)
                    return {"status": "success", "message": "Flood data saved to local file"}
                else:
                    return {"status": "error", "message": "Invalid data format"}
            except Exception as e:
                print(f"Error saving to local file: {e}")
                return {"status": "error", "message": str(e)}
    
    def _convert_flood_report_to_geojson(self, report):
        """Convert a flood report object to GeoJSON Feature"""
        coords = report.get('coordinates', {})
        lat = coords.get('lat', 0)
        lng = coords.get('lng', 0)
        
        properties = {
            "id": report.get('id', ''),
            "location": report.get('location', ''),
            "severity": report.get('severity', '').lower(),
            "category": report.get('category', ''),
            "description": report.get('description', ''),
            "reported_by": report.get('reporter', 'Anonymous'),
            "confidence": report.get('confidence', 0),
            "timestamp": report.get('timestamp', ''),
            "verified": report.get('verified', False),
            "status": "active" if report.get('verified', False) else "pending"
        }
        
        if 'imageUrl' in report:
            properties['photo_url'] = report['imageUrl']
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "properties": properties
        }
        return feature
    
    def _convert_to_dynamodb_item(self, data):
        """Convert data to DynamoDB item format"""
        item = {}
        for key, value in data.items():
            if isinstance(value, dict):
                item[key] = self._convert_to_dynamodb_item(value)
            elif isinstance(value, list):
                item[key] = [self._convert_to_dynamodb_item(v) if isinstance(v, dict) else v for v in value]
            elif isinstance(value, (int, float)):
                item[key] = value
            elif isinstance(value, bool):
                item[key] = value
            else:
                item[key] = str(value) if value is not None else None
        return item
