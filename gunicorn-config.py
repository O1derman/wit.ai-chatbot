# Gunicorn configuration file.

# Bind to all IP addresses of the container
bind = '0.0.0.0:5000'

# Use 4 worker processes for handling requests
workers = 4

# Use threads for handling requests
threads = 2

# Specify timeout in order to prevent hanging Gunicorn processes
timeout = 120
