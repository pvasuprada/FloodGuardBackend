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

## 2. GET /api/reported-floods-geojsonlayer

Fetch reported floods data from AWS DynamoDB or local file and return as GeoJSON (for map layer display).

**Method:** `GET`  
**Endpoint:** `/api/reported-floods-geojsonlayer`  
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
        "coordinates": [78.4772, 17.4065]
      },
      "properties": {
        "id": "1",
        "location": "Banjara Hills",
        "severity": "moderate",
        "category": "Flooding",
        "description": "Water accumulation near Banjara Hills metro station. Road partially blocked.",
        "reported_by": "Raj Kumar",
        "confidence": 85,
        "timestamp": "2h ago",
        "verified": true,
        "status": "active",
        "photo_url": "/api/placeholder/300/200"
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

## 2a. GET /api/reported-floods-geojsonlayer/hyderabad

Fetch all reported floods data as GeoJSON (same as above endpoint, returns all floods without location filtering).

**Method:** `GET`  
**Endpoint:** `/api/reported-floods-geojsonlayer/hyderabad`  
**Request Body:** None

**Response:** Same format as `/api/reported-floods-geojsonlayer`

---

## 2b. GET /api/reported-floods

Fetch reported floods data as structured array format (for UI display).

**Method:** `GET`  
**Endpoint:** `/api/reported-floods`  
**Request Body:** None

**Response (200 OK):**

```json
[
  {
    "id": "1",
    "location": "Banjara Hills",
    "severity": "Moderate",
    "category": "Flooding",
    "description": "Water accumulation near Banjara Hills metro station. Road partially blocked.",
    "reporter": "Raj Kumar",
    "confidence": 85,
    "timestamp": "2h ago",
    "verified": true,
    "imageUrl": "/api/placeholder/300/200",
    "coordinates": {
      "lat": 17.4065,
      "lng": 78.4772
    }
  },
  {
    "id": "2",
    "location": "Kukatpally",
    "severity": "High",
    "category": "Flooding",
    "description": "Severe flooding in residential areas. Water level rising rapidly.",
    "reporter": "Priya Sharma",
    "confidence": 92,
    "timestamp": "1h ago",
    "verified": true,
    "imageUrl": "/api/placeholder/300/200",
    "coordinates": {
      "lat": 17.4849,
      "lng": 78.4138
    }
  }
]
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

## 4. POST /api/report-flood

Post new reported flood data to AWS DynamoDB or local file.

**Method:** `POST`  
**Endpoint:** `/api/report-flood`  
**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field            | Type   | Required | Description                                          |
| ---------------- | ------ | -------- | ---------------------------------------------------- |
| `location`       | string | Yes      | Location name (e.g., "Banjara Hills")                |
| `severity_level` | string | Yes      | Severity level (e.g., "low", "medium", "high")       |
| `description`    | string | No       | Description text (max 500 characters)                |
| `your_name`      | string | No       | Reporter name (leave blank for anonymous)            |
| `photo_evidence` | file   | No       | Image file (PNG, JPG up to 10MB)                     |
| `latitude`       | number | No       | Latitude coordinate (defaults to 0 if not provided)  |
| `longitude`      | number | No       | Longitude coordinate (defaults to 0 if not provided) |

**Example Request (cURL):**

```bash
curl -X POST http://localhost:3001/api/report-flood \
  -F "location=Banjara Hills" \
  -F "severity_level=high" \
  -F "description=Severe flooding observed in the area" \
  -F "your_name=John Doe" \
  -F "latitude=17.4486" \
  -F "longitude=78.3908" \
  -F "photo_evidence=@/path/to/image.jpg"
```

**Example Request (JavaScript/FormData):**

```javascript
const formData = new FormData();
formData.append("location", "Banjara Hills");
formData.append("severity_level", "high");
formData.append("description", "Severe flooding observed");
formData.append("your_name", "John Doe");
formData.append("latitude", "17.4486");
formData.append("longitude", "78.3908");
formData.append("photo_evidence", fileInput.files[0]);

fetch("http://localhost:3001/api/report-flood", {
  method: "POST",
  body: formData,
});
```

**Response Format:**

The API creates a GeoJSON Feature with the following structure:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [longitude, latitude]
  },
  "properties": {
    "id": "uuid",
    "location": "Banjara Hills",
    "severity": "high",
    "description": "Severe flooding observed",
    "reported_by": "John Doe",
    "timestamp": "2024-01-15T10:30:00Z",
    "status": "active",
    "photo_url": "/uploads/uuid_filename.jpg"
  }
}
```

**Success Response (201 Created):**

```json
{
  "status": "success",
  "message": "Flood data posted successfully"
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
  "error": "Location is required"
}
```

```json
{
  "error": "Severity level is required"
}
```

```json
{
  "error": "Description must be 500 characters or less"
}
```

```json
{
  "error": "File size exceeds 10MB limit"
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

### 2. Get Reported Floods (GeoJSON for Map Layer)

```bash
curl -X GET http://localhost:3001/api/reported-floods-geojsonlayer
```

### 2a. Get Reported Floods (Structured Array for UI)

```bash
curl -X GET http://localhost:3001/api/reported-floods
```

### 2b. Get Reported Floods for Hyderabad (GeoJSON)

```bash
curl -X GET http://localhost:3001/api/reported-floods-geojsonlayer/hyderabad
```

### 3. Get Rain Gauge Data

```bash
curl -X GET http://localhost:3001/api/rain-gauge
```

### 4. Post Reported Flood

```bash
curl -X POST http://localhost:3001/api/report-flood \
  -F "location=Banjara Hills" \
  -F "severity_level=high" \
  -F "description=Severe flooding observed in the area" \
  -F "your_name=John Doe" \
  -F "latitude=17.4486" \
  -F "longitude=78.3908"
```

**With Photo Upload:**

```bash
curl -X POST http://localhost:3001/api/report-flood \
  -F "location=Banjara Hills" \
  -F "severity_level=high" \
  -F "description=Severe flooding observed" \
  -F "your_name=John Doe" \
  -F "latitude=17.4486" \
  -F "longitude=78.3908" \
  -F "photo_evidence=@/path/to/image.jpg"
```

### 5. Health Check

```bash
curl -X GET http://localhost:3001/health
```
