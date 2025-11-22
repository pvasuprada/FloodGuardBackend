# FloodGuard Backend API Documentation

Base URL: `http://localhost:3001`

---

## 1. GET /api/floodrisk

Fetch Flood Risk GeoJSON data from AWS S3 or local file.

**Method:** `GET`  
**Endpoint:** `/api/floodrisk`  
**Request Body:** None

**Response (200 OK):**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-122.4194, 37.7749], ...]]
      },
      "properties": {
        "id": 1,
        "name": "Flood Zone A",
        "severity": "high",
        "area_km2": 2.5,
        "last_updated": "2024-01-15T10:30:00Z"
      }
    }
  ]
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch GeoJSON data"
}
```

---

## 2. GET /api/reported-floods

Fetch reported floods data from AWS DynamoDB or local file and return as GeoJSON.

**Method:** `GET`  
**Endpoint:** `/api/reported-floods`  
**Request Body:** None

**Response (200 OK):**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "id": "RF001",
        "reported_by": "user123",
        "timestamp": "2024-01-15T10:30:00Z",
        "severity": "high",
        "water_level_cm": 45,
        "description": "Flooding reported in downtown area",
        "status": "active",
        "reporter_contact": "user@example.com"
      }
    }
  ]
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch reported floods data"
}
```

---

## 3. GET /api/rain-gauge

Fetch rain gauge data from AWS DynamoDB or local file and return as GeoJSON.

**Method:** `GET`  
**Endpoint:** `/api/rain-gauge`  
**Request Body:** None

**Response (200 OK):**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "gauge_id": "RG001",
        "name": "Rain Gauge Station 1",
        "location": "Downtown",
        "rainfall_mm": 45.5,
        "rainfall_24h_mm": 120.3,
        "timestamp": "2024-01-15T12:00:00Z",
        "status": "active",
        "elevation_m": 15.2
      }
    }
  ]
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch rain gauge data"
}
```

---

## 4. POST /api/reported-floods

Post new reported flood data to AWS DynamoDB or local file.

**Method:** `POST`  
**Endpoint:** `/api/reported-floods`  
**Content-Type:** `application/json`

**Request Body:**

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-122.4194, 37.7749]
  },
  "properties": {
    "reported_by": "user123",
    "timestamp": "2024-01-15T10:30:00Z",
    "severity": "high",
    "water_level_cm": 45,
    "description": "Flooding reported in downtown area",
    "status": "active",
    "reporter_contact": "user@example.com"
  }
}
```

**Alternative Request Body (without geometry, coordinates will be extracted from properties):**

```json
{
  "reported_by": "user123",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timestamp": "2024-01-15T10:30:00Z",
  "severity": "high",
  "water_level_cm": 45,
  "description": "Flooding reported in downtown area",
  "status": "active",
  "reporter_contact": "user@example.com"
}
```

**Success Response (201 Created):**

```json
{
  "status": "success",
  "message": "Flood data posted successfully"
}
```

**Error Responses:**

**400 Bad Request:**

```json
{
  "error": "No data provided"
}
```

**500 Internal Server Error:**

```json
{
  "status": "error",
  "message": "Error message details"
}
```

---

## 5. GET /health

Health check endpoint to verify API status and current data source.

**Method:** `GET`  
**Endpoint:** `/health`  
**Request Body:** None

**Response (200 OK):**

```json
{
  "status": "healthy",
  "data_source": "AWS"
}
```

or

```json
{
  "status": "healthy",
  "data_source": "local"
}
```

---

## Example cURL Commands

### 1. Get GeoJSON

```bash
curl -X GET http://localhost:3001/api/floodrisk
```

### 2. Get Reported Floods

```bash
curl -X GET http://localhost:3001/api/reported-floods
```

### 3. Get Rain Gauge Data

```bash
curl -X GET http://localhost:3001/api/rain-gauge
```

### 4. Post Reported Flood

```bash
curl -X POST http://localhost:3001/api/reported-floods \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Feature",
    "geometry": {
      "type": "Point",
      "coordinates": [-122.4194, 37.7749]
    },
    "properties": {
      "reported_by": "user123",
      "timestamp": "2024-01-15T10:30:00Z",
      "severity": "high",
      "water_level_cm": 45,
      "description": "Flooding reported in downtown area",
      "status": "active",
      "reporter_contact": "user@example.com"
    }
  }'
```

### 5. Health Check

```bash
curl -X GET http://localhost:3001/health
```
