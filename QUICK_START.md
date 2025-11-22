# Quick Start Guide

## Starting the Server

### Method 1: Direct Python Command
```bash
python app.py
```

or

```bash
python3 app.py
```

### Method 2: Using Flask CLI (if installed)
```bash
flask run --host=0.0.0.0 --port=3001
```

### What You'll See
When the server starts successfully, you'll see:
```
 * Running on http://0.0.0.0:3001
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
```

The API will be available at: `http://localhost:3001`

## Stopping the Server

### Method 1: Keyboard Interrupt
Press `Ctrl + C` in the terminal where the server is running.

### Method 2: Kill Process by Port
If the server is running in the background or another terminal:

**On macOS/Linux:**
```bash
# Find the process using port 3001
lsof -ti:3001

# Kill the process
kill -9 $(lsof -ti:3001)
```

**On Windows:**
```cmd
# Find the process using port 3001
netstat -ano | findstr :3001

# Kill the process (replace PID with the actual process ID)
taskkill /PID <PID> /F
```

## First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify configuration:**
   - Check `config.yaml` exists
   - Set `data_source` to `'local'` or `'AWS'`

3. **Start the server:**
   ```bash
   python app.py
   ```

4. **Test the API:**
   ```bash
   curl http://localhost:3001/health
   ```

## Running in Background (Optional)

### Using nohup (macOS/Linux)
```bash
nohup python app.py > server.log 2>&1 &
```

To stop:
```bash
kill $(lsof -ti:3001)
```

### Using screen (macOS/Linux)
```bash
# Start a new screen session
screen -S floodguard

# Run the server
python app.py

# Detach: Press Ctrl+A then D

# Reattach later
screen -r floodguard

# Stop: Press Ctrl+C, then type 'exit'
```

## Troubleshooting

### Port Already in Use
If you see "Address already in use":
```bash
# Find what's using port 3001
lsof -ti:3001

# Kill it
kill -9 $(lsof -ti:3001)

# Or use a different port (edit app.py line 115)
app.run(debug=True, host='0.0.0.0', port=3001)
```

### Module Not Found Errors
```bash
# Make sure you're in the project directory
cd /Users/vasupradapottumuttu/Desktop/projects/FloodGuardBackend

# Install dependencies
pip install -r requirements.txt
```

