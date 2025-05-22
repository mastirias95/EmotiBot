import os
from waitress import serve
from app import create_app

# Force enable metrics in development mode
os.environ['DEBUG_METRICS'] = '1'

# Create app
app = create_app()

print("EmotiBot running with Waitress at http://localhost:5000")
print("Metrics available at http://localhost:5000/metrics")

# Run with Waitress
serve(app, host='0.0.0.0', port=5000) 