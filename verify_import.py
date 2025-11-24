"""
Quick script to verify the imported weather stations data
"""
import yaml
import psycopg2
from psycopg2.extras import RealDictCursor


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


def verify_import():
    """Verify the imported weather stations"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM weather_stations")
        total = cursor.fetchone()['total']
        
        # Get unique gauge_ids
        cursor.execute("SELECT COUNT(DISTINCT gauge_id) as unique_ids FROM weather_stations")
        unique = cursor.fetchone()['unique_ids']
        
        # Get sample records
        cursor.execute("""
            SELECT gauge_id, name, location, rainfall_mm, temperature, humidity, last_updated
            FROM weather_stations
            ORDER BY gauge_id
            LIMIT 5
        """)
        samples = cursor.fetchall()
        
        print("=" * 60)
        print("Weather Stations Import Verification")
        print("=" * 60)
        print(f"Total stations imported: {total}")
        print(f"Unique gauge IDs: {unique}")
        print("\nSample records (first 5):")
        print("-" * 60)
        for row in samples:
            print(f"Gauge ID: {row['gauge_id']}")
            print(f"  Name: {row['name']}")
            print(f"  Location: {row['location']}")
            print(f"  Rainfall: {row['rainfall_mm']} mm")
            print(f"  Temperature: {row['temperature']}°C")
            print(f"  Humidity: {row['humidity']}%")
            print(f"  Last Updated: {row['last_updated']}")
            print()
        
        # Check for stations with coordinates
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM weather_stations 
            WHERE geom IS NOT NULL
        """)
        with_coords = cursor.fetchone()['count']
        print(f"Stations with valid coordinates: {with_coords}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error verifying import: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    verify_import()

