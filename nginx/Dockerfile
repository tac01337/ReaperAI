# Use an existing docker image as a base
FROM nginx:latest

# Copy static files to Nginx directory
COPY ./nginx.conf /etc/nginx/nginx.conf
# Expose port 80
EXPOSE 80

# Default command
CMD ["nginx", "-g", "daemon off;"]