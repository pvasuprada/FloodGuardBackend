# Troubleshooting Guide

## "Forbidden" Error in Postman

If you're getting a "Forbidden" (403) error in Postman, follow these steps:

### 1. Verify the Server is Running

Make sure the Flask server is running:
```bash
python app.py
```

You should see output like:
```
 * Running on http://0.0.0.0:3001
 * Debug mode: on
```

### 2. Check the URL in Postman

Make sure you're using the correct URL:
- **Correct:** `http://localhost:3001/api/floodrisk`
- **Wrong:** `https://localhost:3001/api/floodrisk` (don't use https)
- **Wrong:** `http://127.0.0.1:3001/api/floodrisk` (should work, but try localhost first)

### 3. Verify the Request Method

- For GET requests: Select **GET** method in Postman
- For POST requests: Select **POST** method in Postman
- Make sure the endpoint matches the method (e.g., `/api/reported-floods` supports both GET and POST)

### 4. Check Headers in Postman

For **POST** requests, make sure you have:
- **Content-Type:** `application/json` in the Headers tab

### 5. Test with Health Endpoint First

Try the simplest endpoint first:
```
GET http://localhost:3001/health
```

This should return:
```json
{
  "status": "healthy",
  "data_source": "local"
}
```

### 6. Common Postman Settings

1. **Disable SSL verification** (if testing locally):
   - Go to Settings → General
   - Turn off "SSL certificate verification"

2. **Check for Proxy Settings**:
   - Go to Settings → Proxy
   - Make sure proxy is disabled for localhost

### 7. Restart the Server

If you made changes to the code:
1. Stop the server (Ctrl+C)
2. Restart it: `python app.py`

### 8. Check for Port Conflicts

If port 3001 is already in use:
```bash
lsof -ti:3001
```

If something is using it, either:
- Kill the process: `kill -9 <PID>`
- Or change the port in `app.py` (line 115)

### 9. Verify Dependencies

Make sure all packages are installed:
```bash
pip install -r requirements.txt
```

### 10. Check Console Output

Look at the terminal where the Flask app is running. Any errors will be displayed there.

## Common Error Messages

### "Data service not initialized"
- Check if `config.yaml` exists
- Verify the config file is valid YAML

### "Failed to fetch GeoJSON data"
- If using local mode, check if `sample_data/floodrisk.geojson` exists
- If using AWS mode, verify AWS credentials

### Connection Refused
- Server is not running
- Wrong port number
- Firewall blocking the connection

## Testing with cURL

If Postman still doesn't work, test with cURL:

```bash
# Health check
curl http://localhost:3001/health

# Get GeoJSON
curl http://localhost:3001/api/floodrisk

# Get Reported Floods
curl http://localhost:3001/api/reported-floods

# Post Reported Flood
curl -X POST http://localhost:3001/api/reported-floods \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Feature",
    "geometry": {
      "type": "Point",
      "coordinates": [-122.4194, 37.7749]
    },
    "properties": {
      "reported_by": "test_user",
      "severity": "high",
      "water_level_cm": 45,
      "description": "Test flood report"
    }
  }'
```

