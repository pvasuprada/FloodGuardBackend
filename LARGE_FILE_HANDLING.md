# Large File Handling

## Problem
The `floodrisk.geojson` file is 605MB, which can cause "Maximum response size reached" errors in clients.

## Solution Implemented

The `/api/floodrisk` endpoint now uses **file streaming** for large files (>10MB):

1. **Streaming**: Files are streamed directly from disk without loading into memory
2. **Chunked Transfer**: Uses chunked transfer encoding for efficient delivery
3. **Range Requests**: Supports HTTP range requests for partial downloads

## How It Works

- **Small files (<10MB)**: Loaded normally into memory and returned as JSON
- **Large files (>10MB)**: Streamed directly using Flask's `send_file()` which:
  - Streams the file in chunks
  - Doesn't load entire file into memory
  - Supports range requests (for resumable downloads)
  - Handles large files efficiently

## Client Configuration

### Postman
- Postman has a default response size limit
- For very large responses, consider:
  1. Using a browser instead
  2. Downloading the file directly
  3. Using range requests to get parts of the file

### Browser/Frontend
- Modern browsers handle large streaming responses well
- The response will stream progressively
- Consider showing a loading indicator

### cURL
```bash
# Download the file
curl -o floodrisk.geojson http://localhost:3001/api/floodrisk

# With compression (if server supports it)
curl -H "Accept-Encoding: gzip" -o floodrisk.geojson.gz http://localhost:3001/api/floodrisk
```

## Alternative Solutions

If you still encounter issues, consider:

1. **Split the file**: Break into smaller GeoJSON files by region
2. **Use pagination**: Implement pagination to return features in batches
3. **Use a CDN**: Serve the file from a CDN (S3, CloudFront, etc.)
4. **Compress on server**: Pre-compress the file and serve the .gz version
5. **Use a different format**: Consider using a more efficient format like GeoPackage or MBTiles

## Performance Tips

- The first request may take time to start streaming (file I/O)
- Subsequent requests will be faster (OS file cache)
- Consider using a reverse proxy (nginx) with gzip compression
- For production, consider using a web server (nginx, Apache) to serve static files

