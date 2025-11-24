-- FloodGuard Backend PostgreSQL Schema
-- This file creates the necessary tables for the FloodGuard application

-- Enable PostGIS extension for spatial data support
CREATE EXTENSION IF NOT EXISTS postgis;

-- Table: reported_floods
-- Stores user-reported flood incidents
CREATE TABLE IF NOT EXISTS reported_floods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('low', 'medium', 'moderate', 'high')),
    category VARCHAR(100) DEFAULT 'Flooding',
    description TEXT,
    reported_by VARCHAR(255) DEFAULT 'Anonymous',
    confidence INTEGER DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'pending', 'resolved', 'false_alarm')),
    photo_url VARCHAR(500),
    -- Spatial data using PostGIS POINT geometry
    geom GEOMETRY(POINT, 4326) NOT NULL,
    -- Indexes for better query performance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on geometry column for faster spatial queries
CREATE INDEX IF NOT EXISTS idx_reported_floods_geom ON reported_floods USING GIST (geom);

-- Create indexes on commonly queried columns
CREATE INDEX IF NOT EXISTS idx_reported_floods_location ON reported_floods (location);
CREATE INDEX IF NOT EXISTS idx_reported_floods_severity ON reported_floods (severity);
CREATE INDEX IF NOT EXISTS idx_reported_floods_status ON reported_floods (status);
CREATE INDEX IF NOT EXISTS idx_reported_floods_timestamp ON reported_floods (timestamp);
CREATE INDEX IF NOT EXISTS idx_reported_floods_verified ON reported_floods (verified);

-- Table: weather_stations
-- Stores weather station/rain gauge data
CREATE TABLE IF NOT EXISTS weather_stations (
    id SERIAL PRIMARY KEY,
    gauge_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    mandal_name VARCHAR(255),
    rainfall_mm DECIMAL(10, 2),
    temperature DECIMAL(5, 2),
    humidity DECIMAL(5, 2),
    date_time DATE,
    last_updated TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance')),
    -- Spatial data using PostGIS POINT geometry
    geom GEOMETRY(POINT, 4326) NOT NULL,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on geometry column for faster spatial queries
CREATE INDEX IF NOT EXISTS idx_weather_stations_geom ON weather_stations USING GIST (geom);

-- Create indexes on commonly queried columns
CREATE INDEX IF NOT EXISTS idx_weather_stations_gauge_id ON weather_stations (gauge_id);
CREATE INDEX IF NOT EXISTS idx_weather_stations_location ON weather_stations (location);
CREATE INDEX IF NOT EXISTS idx_weather_stations_status ON weather_stations (status);
CREATE INDEX IF NOT EXISTS idx_weather_stations_date_time ON weather_stations (date_time);

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at column
CREATE TRIGGER update_reported_floods_updated_at BEFORE UPDATE ON reported_floods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_weather_stations_updated_at BEFORE UPDATE ON weather_stations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE reported_floods IS 'Stores user-reported flood incidents with spatial location data';
COMMENT ON TABLE weather_stations IS 'Stores weather station and rain gauge data with spatial location';
COMMENT ON COLUMN reported_floods.geom IS 'PostGIS POINT geometry in WGS84 (SRID 4326)';
COMMENT ON COLUMN weather_stations.geom IS 'PostGIS POINT geometry in WGS84 (SRID 4326)';

