"""
Data service module for handling AWS and local data sources
"""
import yaml
import json
import geopandas as gpd
import pandas as pd
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


class DataService:
    def __init__(self, config_path='config.yaml'):
        """Initialize data service with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.data_source = self.config.get('data_source', 'local')
        
        if self.data_source == 'AWS':
            self._init_aws_clients()
    
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
    
    def fetch_geojson(self):
        """Fetch GeoJSON from AWS S3 or local file"""
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
            # Local mode
            local_config = self.config.get('local', {})
            geojson_path = local_config.get('geojson_path', 'sample_data/floodrisk.geojson')
            try:
                # Read GeoJSON file directly as JSON
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
    
    def _convert_flood_report_to_geojson(self, report):
        """Convert a flood report object to GeoJSON Feature"""
        coords = report.get('coordinates', {})
        lat = coords.get('lat', 0)
        lng = coords.get('lng', 0)
        
        # Map fields to GeoJSON properties
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
        
        # Add imageUrl if present
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
    
    def fetch_reported_floods(self):
        """Fetch reported floods from AWS DynamoDB or local file and convert to GeoJSON"""
        if self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                response = table.scan()
                items = response.get('Items', [])
                
                # Convert DynamoDB items to GeoJSON
                features = []
                for item in items:
                    # Handle different possible field names from DynamoDB
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
            # Local mode - read from sample data JSON and convert to GeoJSON
            local_config = self.config.get('local', {})
            floods_path = local_config.get('reported_floods_path', 'sample_data/reported_floods.json')
            try:
                # Try to read as structured JSON first
                with open(floods_path, 'r') as f:
                    data = json.load(f)
                
                # Check if it's already GeoJSON or structured array
                if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
                    # Already GeoJSON
                    return data
                elif isinstance(data, list):
                    # Structured array - convert to GeoJSON
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
            except FileNotFoundError:
                print(f"Error: Reported floods file not found at {floods_path}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in reported floods file: {e}")
                return None
            except Exception as e:
                print(f"Error reading local reported floods: {e}")
                return None
    
    def fetch_reported_floods_structured(self):
        """Fetch reported floods as structured array format (for UI display)"""
        if self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                response = table.scan()
                items = response.get('Items', [])
                
                # Convert DynamoDB items to structured format
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
                    
                    # Add imageUrl if present
                    if 'photo_url' in item or 'imageUrl' in item:
                        report['imageUrl'] = str(item.get('photo_url') or item.get('imageUrl', ''))
                    
                    reports.append(report)
                
                return reports
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
                
                # If it's already a structured array, return it
                if isinstance(data, list):
                    return data
                # If it's GeoJSON, convert to structured format
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
            except FileNotFoundError:
                print(f"Error: Reported floods file not found at {floods_path}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in reported floods file: {e}")
                return None
            except Exception as e:
                print(f"Error reading local reported floods: {e}")
                return None
    
    def fetch_reported_floods_by_location(self, location_filter):
        """Fetch reported floods filtered by location from AWS DynamoDB or local file and convert to GeoJSON"""
        if self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                response = table.scan()
                items = response.get('Items', [])
                
                # Convert DynamoDB items to GeoJSON and filter by location
                features = []
                for item in items:
                    # Check if location matches the filter (case-insensitive)
                    item_location = str(item.get('location', '')).lower()
                    if location_filter.lower() in item_location or item_location in location_filter.lower():
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
            floods_path = local_config.get('reported_floods_path', 'sample_data/heatmap.geojson')
            try:
                # Read GeoJSON file directly as JSON
                with open(floods_path, 'r') as f:
                    geojson_data = json.load(f)
                
                # Filter features by location
                if 'features' in geojson_data:
                    filtered_features = []
                    for feature in geojson_data['features']:
                        if 'properties' in feature and 'location' in feature['properties']:
                            feature_location = str(feature['properties']['location']).lower()
                            if location_filter.lower() in feature_location or feature_location in location_filter.lower():
                                filtered_features.append(feature)
                    
                    geojson_data['features'] = filtered_features
                
                return geojson_data
            except FileNotFoundError:
                print(f"Error: Reported floods file not found at {floods_path}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in reported floods file: {e}")
                return None
            except Exception as e:
                print(f"Error reading local reported floods: {e}")
                return None
    
    def fetch_rain_gauge(self):
        """Fetch rain gauge data from AWS DynamoDB or local file and convert to GeoJSON"""
        if self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_rain_gauge)
                response = table.scan()
                items = response.get('Items', [])
                
                # Convert DynamoDB items to GeoJSON
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
                # Read GeoJSON file directly as JSON
                with open(rain_gauge_path, 'r') as f:
                    geojson_data = json.load(f)
                return geojson_data
            except FileNotFoundError:
                print(f"Error: Rain gauge file not found at {rain_gauge_path}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in rain gauge file: {e}")
                return None
            except Exception as e:
                print(f"Error reading local rain gauge: {e}")
                return None
    
    def post_reported_flood(self, flood_data):
        """Post reported flood data to AWS DynamoDB"""
        if self.data_source == 'AWS':
            try:
                table = self.dynamodb.Table(self.dynamodb_table_reported_floods)
                
                # Extract coordinates from GeoJSON if present
                if 'geometry' in flood_data:
                    coords = flood_data['geometry'].get('coordinates', [])
                    if len(coords) >= 2:
                        flood_data['longitude'] = coords[0]
                        flood_data['latitude'] = coords[1]
                
                # Convert to DynamoDB format
                dynamodb_item = self._convert_to_dynamodb_item(flood_data)
                
                response = table.put_item(Item=dynamodb_item)
                return {"status": "success", "message": "Flood data posted successfully"}
            except ClientError as e:
                print(f"Error posting to DynamoDB: {e}")
                return {"status": "error", "message": str(e)}
        else:
            # Local mode - append to local file
            local_config = self.config.get('local', {})
            floods_path = local_config.get('reported_floods_path', 'sample_data/heatmap.geojson')
            try:
                # Read existing data
                if Path(floods_path).exists():
                    with open(floods_path, 'r') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = {"type": "FeatureCollection", "features": []}
                
                # Add new feature
                if isinstance(flood_data, dict):
                    if 'type' in flood_data and flood_data['type'] == 'Feature':
                        # It's already a Feature
                        existing_data['features'].append(flood_data)
                    elif 'geometry' in flood_data and 'properties' in flood_data:
                        # It's a Feature without the type field
                        feature = {
                            "type": "Feature",
                            "geometry": flood_data['geometry'],
                            "properties": flood_data['properties']
                        }
                        existing_data['features'].append(feature)
                    else:
                        return {"status": "error", "message": "Invalid GeoJSON format"}
                    
                    # Write back to file
                    with open(floods_path, 'w') as f:
                        json.dump(existing_data, f, indent=2)
                    return {"status": "success", "message": "Flood data saved to local file"}
                else:
                    return {"status": "error", "message": "Invalid data format"}
            except Exception as e:
                print(f"Error saving to local file: {e}")
                return {"status": "error", "message": str(e)}
    
    def _convert_to_dynamodb_item(self, data):
        """Convert data to DynamoDB item format"""
        item = {}
        for key, value in data.items():
            if isinstance(value, dict):
                item[key] = self._convert_to_dynamodb_item(value)
            elif isinstance(value, list):
                item[key] = [self._convert_to_dynamodb_item(v) if isinstance(v, dict) else v for v in value]
            elif isinstance(value, (int, float)):
                # DynamoDB supports numbers natively
                item[key] = value
            elif isinstance(value, bool):
                item[key] = value
            else:
                item[key] = str(value) if value is not None else None
        return item

