# Use the official Docker Hub Postgres image
FROM postgres:latest

# Set the working directory in the Docker container
WORKDIR /docker-entrypoint-initdb.d/

ENV POSTGRES_DB=memory
ENV POSTGRES_USER=user
ENV POSTGRES_PASSWORD=mysecretpassword

# Copy the database schema to the docker entrypoint directory
COPY ./schema/* /docker-entrypoint-initdb.d/