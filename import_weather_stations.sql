-- SQL script to import weather stations from CSV
-- Note: This requires the CSV to be accessible by PostgreSQL server
-- For local imports, use the Python script instead

-- First, create a temporary table to hold the raw CSV data
CREATE TEMP TABLE temp_weather_stations (
    aws_id VARCHAR(50),
    aws_location VARCHAR(255),
    mandal_name VARCHAR(255),
    date_time_str VARCHAR(50),
    last_updated_str VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    rainfall_mm DECIMAL(10, 2),
    temperature DECIMAL(5, 2),
    humidity DECIMAL(5, 2)
);

-- Copy data from CSV (adjust path as needed)
-- Note: The file must be accessible by the PostgreSQL server user
COPY temp_weather_stations (
    aws_id, aws_location, mandal_name, date_time_str, last_updated_str,
    latitude, longitude, rainfall_mm, temperature, humidity
)
FROM '/Users/vasupradapottumuttu/Downloads/aws_data_9pm.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Insert into weather_stations table with proper date parsing and geometry
INSERT INTO weather_stations (
    gauge_id, name, location, mandal_name, rainfall_mm,
    temperature, humidity, date_time, last_updated, status, geom
)
SELECT 
    aws_id,
    aws_location,
    aws_location,
    NULLIF(mandal_name, ''),
    NULLIF(rainfall_mm, 0),
    NULLIF(temperature, 0),
    NULLIF(humidity, 0),
    CASE 
        WHEN date_time_str ~ '^\d{2}/\d{2}/\d{4}$' 
        THEN to_date(date_time_str, 'DD/MM/YYYY')
        ELSE NULL
    END,
    CASE 
        WHEN last_updated_str ~ '^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$'
        THEN to_timestamp(last_updated_str, 'DD/MM/YYYY HH24:MI')
        ELSE NULL
    END,
    'active',
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
FROM temp_weather_stations
WHERE aws_id IS NOT NULL 
  AND aws_id != ''
  AND latitude IS NOT NULL 
  AND longitude IS NOT NULL
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
    updated_at = CURRENT_TIMESTAMP;

-- Clean up
DROP TABLE temp_weather_stations;

