FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN npm install

# Build frontend
RUN npm run build

# Serve with static server
RUN npm install -g serve
CMD ["serve", "-s", "dist", "-l", "3000"]