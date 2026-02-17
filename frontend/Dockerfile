# Use an official Node runtime as a parent image
FROM node:18-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose port (Render will override this, but good for documentation)
EXPOSE 3000

# Start the application
# Use the PORT environment variable provided by Render
ENV PORT=3000
CMD npm start -- --port ${PORT:-3000}
