# PostgreSQL Database Setup Guide

This guide will help you set up the PostgreSQL database for the FloodGuard Backend.

## Prerequisites

1. PostgreSQL 12+ installed on your system
2. PostGIS extension available (for spatial data support)

## Step 1: Install PostgreSQL and PostGIS

### macOS (using Homebrew)
```bash
brew install postgresql@18
brew install postgis
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis
```

### Windows
Download and install from [PostgreSQL official website](https://www.postgresql.org/download/windows/)

## Step 2: Create Database

1. Connect to PostgreSQL:
```bash
psql -U postgres
```

2. Create the database:
```sql
CREATE DATABASE FloodGuard;
```

3. Connect to the new database:
```sql
\c FloodGuard
```

4. Enable PostGIS extension:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

## Step 3: Run Schema Script

Run the schema.sql file to create all tables:

```bash
psql -U postgres -d FloodGuard -f schema.sql
```

Or from within psql:
```sql
\i schema.sql
```

## Step 4: Verify Tables

Check that tables were created successfully:

```sql
\dt
```

You should see:
- `reported_floods`
- `weather_stations`

Verify PostGIS is working:
```sql
SELECT PostGIS_version();
```

## Step 5: Configure Connection

Update `config.yaml` with your PostgreSQL credentials:

```yaml
data_source: "postgresql"

postgresql:
  host: "localhost"
  port: 5432
  database: "FloodGuard"
  user: "postgres"
  password: "your_password_here"
  min_connections: 1
  max_connections: 10
```

## Step 6: Test Connection

Run the Flask application:

```bash
python app.py
```

Check the health endpoint:
```bash
curl http://localhost:3001/health
```

## Table Structures

### reported_floods
- `id` (UUID): Primary key
- `location` (VARCHAR): Location name
- `severity` (VARCHAR): low, medium, moderate, high
- `category` (VARCHAR): Category of flood
- `description` (TEXT): Description text
- `reported_by` (VARCHAR): Reporter name
- `confidence` (INTEGER): Confidence level (0-100)
- `timestamp` (TIMESTAMP): When reported
- `verified` (BOOLEAN): Verification status
- `status` (VARCHAR): active, pending, resolved, false_alarm
- `photo_url` (VARCHAR): URL to photo evidence
- `geom` (GEOMETRY): PostGIS point geometry (SRID 4326)

### weather_stations
- `id` (SERIAL): Primary key
- `gauge_id` (VARCHAR): Unique gauge identifier
- `name` (VARCHAR): Station name
- `location` (VARCHAR): Location name
- `mandal_name` (VARCHAR): Mandal/region name
- `rainfall_mm` (DECIMAL): Rainfall in millimeters
- `temperature` (DECIMAL): Temperature
- `humidity` (DECIMAL): Humidity percentage
- `date_time` (DATE): Date of reading
- `last_updated` (TIMESTAMP): Last update time
- `status` (VARCHAR): active, inactive, maintenance
- `geom` (GEOMETRY): PostGIS point geometry (SRID 4326)

## Importing Sample Data (Optional)

If you want to import sample data from the GeoJSON files:

### For weather_stations:
You can use a script to import from `sample_data/rain_gauge.geojson`. Here's a Python example:

```python
import json
import psycopg2
from psycopg2.extras import execute_values

conn = psycopg2.connect(
    host="localhost",
    database="FloodGuard",
    user="postgres",
    password="your_password"
)
cursor = conn.cursor()

with open('sample_data/rain_gauge.geojson', 'r') as f:
    data = json.load(f)

for feature in data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    
    cursor.execute("""
        INSERT INTO weather_stations (
            gauge_id, name, location, mandal_name, rainfall_mm,
            temperature, humidity, date_time, last_updated, status, geom
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
        ST_SetSRID(ST_MakePoint(%s, %s), 4326))
    """, (
        props.get('gauge_id'),
        props.get('name'),
        props.get('location'),
        props.get('mandal_name'),
        props.get('rainfall_mm'),
        props.get('temperature'),
        props.get('humidity'),
        props.get('date_time'),
        props.get('last_updated'),
        props.get('status', 'active'),
        coords[0],  # longitude
        coords[1]   # latitude
    ))

conn.commit()
cursor.close()
conn.close()
```

## Troubleshooting

### Connection Refused
- Ensure PostgreSQL is running: `pg_isready` or `sudo systemctl status postgresql`
- Check firewall settings
- Verify host and port in config.yaml

### PostGIS Not Found
- Install PostGIS extension: `CREATE EXTENSION postgis;`
- Verify installation: `SELECT PostGIS_version();`

### Permission Denied
- Ensure the user has CREATE privileges on the database
- Check PostgreSQL authentication settings in `pg_hba.conf`

### Geometry Errors
- Ensure coordinates are in WGS84 format (longitude, latitude)
- Verify SRID is 4326

## AWS Deployment Notes

When deploying to AWS (RDS PostgreSQL):
1. Update `config.yaml` with RDS endpoint
2. Ensure security groups allow connections from your application
3. PostGIS is available on RDS - no additional setup needed
4. Consider using connection pooling for production workloads

