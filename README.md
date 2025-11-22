# FloodGuard Backend

A Python Flask API backend for managing flood data with support for AWS and local data sources.

## Features

- 4 REST API endpoints for flood data management
- Support for AWS (S3, DynamoDB) and local file data sources
- GeoJSON data handling with GeoPandas
- Configurable data source switching

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to configure your data source:

- Set `data_source` to `'AWS'` or `'local'`
- For AWS mode: Update AWS credentials and resource names
- For local mode: Update file paths if needed

### AWS Configuration
- Update `aws.access_key_id` and `aws.secret_access_key` with your credentials
- Configure S3 bucket name and DynamoDB table names
- Set the appropriate AWS region

### Local Configuration
- GeoJSON files are stored in `sample_data/` folder
- You can replace the dummy GeoJSON files with your own data

## API Endpoints

### 1. GET /api/floodrisk
Fetch Flood Risk GeoJSON data from AWS S3 or local file.

**Response:** GeoJSON FeatureCollection

### 2. GET /api/reported-floods
Fetch reported floods data from AWS DynamoDB or local file and return as GeoJSON.

**Response:** GeoJSON FeatureCollection with reported flood points

### 3. GET /api/rain-gauge
Fetch rain gauge data from AWS DynamoDB or local file and return as GeoJSON.

**Response:** GeoJSON FeatureCollection with rain gauge points

### 4. POST /api/reported-floods
Post new reported flood data to AWS DynamoDB or local file.

**Request Body:** GeoJSON Feature object
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-122.4194, 37.7749]
  },
  "properties": {
    "reported_by": "user123",
    "severity": "high",
    "water_level_cm": 45,
    "description": "Flooding reported"
  }
}
```

**Response:** Success/error message

### Health Check
GET /health - Check API status and current data source

## Running the Application

```bash
python app.py
```

The API will be available at `http://localhost:3001`

## Sample Data

The `sample_data/` folder contains 3 dummy GeoJSON files:
- `floodrisk.geojson` - General flood zone data
- `heatmap.geojson` - Heatmap data (reported flood incidents)
- `rain_gauge.geojson` - Rain gauge station data

You can replace these files with your own GeoJSON data.

## Project Structure

```
FloodGuardBackend/
├── app.py                 # Main Flask application
├── data_service.py        # Data service for AWS/local handling
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── sample_data/           # Sample GeoJSON files
│   ├── floodrisk.geojson
│   ├── heatmap.geojson
│   └── rain_gauge.geojson
└── README.md
```

## Notes

- When using AWS mode, ensure your AWS credentials have proper permissions for S3 and DynamoDB
- The sample AWS credentials in `config.yaml` are placeholders and should be updated
- Local mode reads from and writes to GeoJSON files in the `sample_data/` folder

