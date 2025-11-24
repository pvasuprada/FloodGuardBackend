"""
Script to import weather stations data from aws_data_9pm.csv into PostgreSQL
"""
import csv
import yaml
import psycopg2
from psycopg2.extras import execute_values
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


def parse_date(date_str):
    """Parse date string in format DD/MM/YYYY"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
    except:
        return None


def parse_datetime(datetime_str):
    """Parse datetime string in format DD/MM/YYYY HH:MM"""
    if not datetime_str or datetime_str.strip() == '':
        return None
    try:
        return datetime.strptime(datetime_str.strip(), '%d/%m/%Y %H:%M')
    except:
        return None


def parse_float(value):
    """Parse float value, return None if empty"""
    if not value or value.strip() == '':
        return None
    try:
        return float(value.strip())
    except:
        return None


def import_weather_stations_csv(csv_path):
    """Import weather stations from CSV file"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip BOM if present
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Parse CSV
            reader = csv.DictReader(content.splitlines())
            
            imported = 0
            skipped = 0
            errors = []
            
            for row in reader:
                # Skip empty rows
                if not row.get('AWS ID') or row.get('AWS ID').strip() == '':
                    skipped += 1
                    continue
                
                gauge_id = row.get('AWS ID', '').strip()
                location = row.get('AWS Location', '').strip()
                mandal_name = row.get('Mandal Name', '').strip()
                date_time_str = row.get('Date & Time', '').strip()
                last_updated_str = row.get('Last Updated', '').strip()
                latitude_str = row.get('Latitude', '').strip()
                longitude_str = row.get('Longitude', '').strip()
                rainfall_str = row.get('Rainfall* (mm)', '').strip()
                temperature_str = row.get('Temperature', '').strip()
                humidity_str = row.get('Humidity(%)', '').strip()
                
                # Validate required fields
                if not gauge_id or not location:
                    skipped += 1
                    errors.append(f"Row {imported + skipped}: Missing gauge_id or location")
                    continue
                
                # Parse coordinates
                try:
                    latitude = float(latitude_str) if latitude_str else None
                    longitude = float(longitude_str) if longitude_str else None
                except ValueError:
                    skipped += 1
                    errors.append(f"Row {imported + skipped}: Invalid coordinates for {gauge_id}")
                    continue
                
                if latitude is None or longitude is None:
                    skipped += 1
                    errors.append(f"Row {imported + skipped}: Missing coordinates for {gauge_id}")
                    continue
                
                # Parse dates
                date_time = parse_date(date_time_str)
                last_updated = parse_datetime(last_updated_str)
                
                # Parse numeric values
                rainfall_mm = parse_float(rainfall_str)
                temperature = parse_float(temperature_str)
                humidity = parse_float(humidity_str)
                
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
                        location,  # Using location as name if name column doesn't exist
                        location,
                        mandal_name if mandal_name else None,
                        rainfall_mm,
                        temperature,
                        humidity,
                        date_time,
                        last_updated,
                        'active',  # Default status
                        longitude,  # PostGIS uses (longitude, latitude)
                        latitude
                    ))
                    imported += 1
                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {imported + skipped}: Error importing {gauge_id}: {str(e)}")
                    print(f"Error importing gauge {gauge_id}: {e}")
        
        conn.commit()
        print(f"\nImport Summary:")
        print(f"  Imported: {imported} stations")
        print(f"  Skipped: {skipped} rows")
        
        if errors:
            print(f"\nErrors encountered ({len(errors)}):")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing weather stations: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import sys
    
    csv_path = 'aws_data_9pm.csv'
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    print(f"Importing weather stations from {csv_path}...")
    print("This may take a moment...\n")
    
    try:
        import_weather_stations_csv(csv_path)
        print("\nImport complete!")
    except FileNotFoundError:
        print(f"Error: File '{csv_path}' not found.")
        print("Please provide the correct path to the CSV file.")
        print("Usage: python import_weather_stations_csv.py [path/to/aws_data_9pm.csv]")
    except Exception as e:
        print(f"\nImport failed: {e}")

