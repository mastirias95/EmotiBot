import os
import sys
from app import create_app

# Force metrics to be enabled
os.environ['DEBUG_METRICS'] = '1'

# Create and run the application
app = create_app()
print("EmotiBot running with metrics enabled at http://localhost:5000/metrics")
app.run(host='0.0.0.0', port=5000, debug=True) 