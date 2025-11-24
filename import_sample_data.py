"""
Script to import sample data from GeoJSON files into PostgreSQL
Run this after setting up the database schema
"""
import json
import yaml
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


def get_db_connection():
    """Get database connection from config"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    pg_config = config.get('postgresql', {})
    return psycopg2.connect(
        host=pg_config.get('host', 'localhost'),
        port=pg_config.get('port', 5432),
        database=pg_config.get('database', 'FloodGuard'),
        user=pg_config.get('user', 'postgres'),
        password=pg_config.get('password', 'postgres')
    )


def import_weather_stations():
    """Import weather stations from rain_gauge.geojson"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open('sample_data/rain_gauge.geojson', 'r') as f:
            data = json.load(f)
        
        imported = 0
        skipped = 0
        
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            coords = feature.get('geometry', {}).get('coordinates', [])
            
            if len(coords) < 2:
                skipped += 1
                continue
            
            gauge_id = props.get('gauge_id')
            if not gauge_id:
                skipped += 1
                continue
            
            # Parse date_time if it's a string
            date_time = props.get('date_time')
            if date_time and isinstance(date_time, str):
                try:
                    # Try parsing different date formats
                    if '/' in date_time:
                        date_time = datetime.strptime(date_time.split()[0], '%d/%m/%Y').date()
                    else:
                        date_time = datetime.strptime(date_time, '%Y-%m-%d').date()
                except:
                    date_time = None
            
            # Parse last_updated if it's a string
            last_updated = props.get('last_updated')
            if last_updated and isinstance(last_updated, str):
                try:
                    # Try parsing different timestamp formats
                    if '/' in last_updated:
                        last_updated = datetime.strptime(last_updated, '%d/%m/%Y %H:%M')
                    else:
                        last_updated = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S')
                except:
                    last_updated = None
            
            try:
                cursor.execute("""
                    INSERT INTO weather_stations (
                        gauge_id, name, location, mandal_name, rainfall_mm,
                        temperature, humidity, date_time, last_updated, status, geom
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    ON CONFLICT (gauge_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        location = EXCLUDED.location,
                        mandal_name = EXCLUDED.mandal_name,
                        rainfall_mm = EXCLUDED.rainfall_mm,
                        temperature = EXCLUDED.temperature,
                        humidity = EXCLUDED.humidity,
                        date_time = EXCLUDED.date_time,
                        last_updated = EXCLUDED.last_updated,
                        status = EXCLUDED.status,
                        geom = EXCLUDED.geom,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    gauge_id,
                    props.get('name'),
                    props.get('location'),
                    props.get('mandal_name'),
                    props.get('rainfall_mm'),
                    props.get('temperature'),
                    props.get('humidity'),
                    date_time,
                    last_updated,
                    props.get('status', 'active'),
                    coords[0],  # longitude
                    coords[1]   # latitude
                ))
                imported += 1
            except Exception as e:
                print(f"Error importing gauge {gauge_id}: {e}")
                skipped += 1
        
        conn.commit()
        print(f"Weather stations: {imported} imported, {skipped} skipped")
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing weather stations: {e}")
    finally:
        cursor.close()
        conn.close()


def import_reported_floods():
    """Import reported floods from reported_floods.json"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open('sample_data/reported_floods.json', 'r') as f:
            data = json.load(f)
        
        imported = 0
        skipped = 0
        
        for report in data:
            coords = report.get('coordinates', {})
            lat = coords.get('lat', 0)
            lng = coords.get('lng', 0)
            
            if lat == 0 and lng == 0:
                skipped += 1
                continue
            
            # Parse timestamp if it's a string
            timestamp = report.get('timestamp')
            if timestamp and isinstance(timestamp, str):
                try:
                    # Handle relative timestamps like "2h ago"
                    if 'ago' in timestamp.lower():
                        timestamp = datetime.utcnow()  # Use current time as approximation
                    else:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = None
            
            # Map severity to lowercase
            severity = report.get('severity', 'low').lower()
            
            try:
                cursor.execute("""
                    INSERT INTO reported_floods (
                        id, location, severity, category, description,
                        reported_by, confidence, timestamp, verified,
                        status, photo_url, geom
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    )
                """, (
                    report.get('location'),
                    severity,
                    report.get('category', 'Flooding'),
                    report.get('description', ''),
                    report.get('reporter', 'Anonymous'),
                    report.get('confidence', 0),
                    timestamp,
                    report.get('verified', False),
                    'active' if report.get('verified', False) else 'pending',
                    report.get('imageUrl'),
                    lng,
                    lat
                ))
                imported += 1
            except Exception as e:
                print(f"Error importing report: {e}")
                skipped += 1
        
        conn.commit()
        print(f"Reported floods: {imported} imported, {skipped} skipped")
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing reported floods: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print("Importing sample data into PostgreSQL...")
    print("\n1. Importing weather stations...")
    import_weather_stations()
    print("\n2. Importing reported floods...")
    import_reported_floods()
    print("\nImport complete!")

