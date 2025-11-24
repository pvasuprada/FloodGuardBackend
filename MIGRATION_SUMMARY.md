# PostgreSQL Migration Summary

## Overview
The FloodGuard Backend has been migrated from AWS DynamoDB/local files to PostgreSQL with PostGIS support for spatial data.

## Changes Made

### 1. Database Schema (`schema.sql`)
Created two main tables:

#### `reported_floods`
- **Primary Key**: `id` (UUID)
- **Spatial Column**: `geom` (PostGIS POINT, SRID 4326)
- **Key Fields**:
  - `location` (VARCHAR): Location name
  - `severity` (VARCHAR): low, medium, moderate, high
  - `category` (VARCHAR): Category of flood
  - `description` (TEXT): Description text
  - `reported_by` (VARCHAR): Reporter name
  - `confidence` (INTEGER): 0-100
  - `timestamp` (TIMESTAMP): When reported
  - `verified` (BOOLEAN): Verification status
  - `status` (VARCHAR): active, pending, resolved, false_alarm
  - `photo_url` (VARCHAR): URL to photo evidence
- **Indexes**: Spatial index on `geom`, indexes on location, severity, status, timestamp, verified

#### `weather_stations`
- **Primary Key**: `id` (SERIAL)
- **Unique Constraint**: `gauge_id` (VARCHAR)
- **Spatial Column**: `geom` (PostGIS POINT, SRID 4326)
- **Key Fields**:
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
- **Indexes**: Spatial index on `geom`, indexes on gauge_id, location, status, date_time

### 2. Configuration (`config.yaml`)
- Added `postgresql` section with connection settings
- Changed default `data_source` to `"postgresql"`
- Kept `local` config for API #1 (floodrisk.geojson) which remains unchanged

### 3. Data Service (`data_service.py`)
- Added PostgreSQL connection pool management
- Updated all methods to support PostgreSQL:
  - `fetch_reported_floods()`: Uses PostGIS `ST_AsGeoJSON()` to convert geometry
  - `fetch_reported_floods_structured()`: Uses `ST_X()` and `ST_Y()` to extract coordinates
  - `fetch_rain_gauge()`: Uses PostGIS for spatial queries
  - `post_reported_flood()`: Uses `ST_MakePoint()` and `ST_SetSRID()` to create geometry
- Maintained backward compatibility with AWS and local modes

### 4. Dependencies (`requirements.txt`)
- Added `psycopg2-binary==2.9.9` for PostgreSQL connectivity

### 5. Application (`app.py`)
- **No changes required** - All endpoints work with the updated data service
- API #1 (`/api/floodrisk`) remains unchanged as requested

## API Endpoints Status

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/floodrisk` | ✅ Unchanged | Still reads from local file |
| `GET /api/reported-floods-geojsonlayer` | ✅ Updated | Now uses PostgreSQL |
| `GET /api/reported-floods-geojsonlayer/hyderabad` | ✅ Updated | Now uses PostgreSQL |
| `GET /api/reported-floods` | ✅ Updated | Now uses PostgreSQL |
| `GET /api/rain-gauge` | ✅ Updated | Now uses PostgreSQL |
| `POST /api/report-flood` | ✅ Updated | Now uses PostgreSQL |
| `GET /health` | ✅ Updated | Shows current data source |

## Setup Instructions

1. **Install PostgreSQL and PostGIS** (see `DATABASE_SETUP.md`)

2. **Create Database**:
   ```bash
   createdb FloodGuard
   psql FloodGuard -c "CREATE EXTENSION postgis;"
   ```

3. **Run Schema**:
   ```bash
   psql FloodGuard -f schema.sql
   ```

4. **Update Config**:
   Edit `config.yaml` with your PostgreSQL credentials

5. **Import Sample Data** (optional):
   ```bash
   python import_sample_data.py
   ```

6. **Run Application**:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

## Table Design Rationale

### Why PostGIS?
- Native support for spatial data types
- Efficient spatial indexing (GIST indexes)
- Built-in functions for GeoJSON conversion
- Industry standard for geospatial applications

### Why UUID for reported_floods.id?
- Globally unique identifiers
- No sequence conflicts in distributed systems
- Better for AWS deployment later

### Why SERIAL for weather_stations.id?
- Simple auto-incrementing integer
- `gauge_id` is the business key (unique constraint)
- More efficient for large datasets

### Index Strategy
- **Spatial indexes (GIST)**: Fast spatial queries
- **B-tree indexes**: Fast lookups on common filters (location, severity, status)
- **Composite indexes**: Could be added later if needed for specific query patterns

## Data Types Recommendations

All data types have been carefully chosen:

- **VARCHAR with appropriate lengths**: Based on actual data requirements
- **TEXT for descriptions**: Unlimited length for user descriptions
- **DECIMAL for measurements**: Precise numeric values for rainfall, temperature, humidity
- **TIMESTAMP WITH TIME ZONE**: Proper timezone handling
- **BOOLEAN**: Clear true/false values
- **CHECK constraints**: Data validation at database level
- **DEFAULT values**: Sensible defaults for optional fields

## Next Steps

1. **Test the APIs** with your PostgreSQL database
2. **Import existing data** using `import_sample_data.py`
3. **Update connection settings** in `config.yaml` for production
4. **Deploy to AWS RDS** when ready (PostGIS is available on RDS)

## AWS Deployment Notes

When deploying to AWS:
- Use Amazon RDS PostgreSQL (PostGIS extension available)
- Update `config.yaml` with RDS endpoint
- Configure security groups appropriately
- Consider using RDS Proxy for connection pooling
- Use environment variables for sensitive credentials

