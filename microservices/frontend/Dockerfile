FROM nginx:alpine

# Copy the frontend files to nginx
COPY index.html /usr/share/nginx/html/
COPY . /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 