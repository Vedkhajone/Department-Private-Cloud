FROM node:20-alpine

WORKDIR /app

# Install dependencies first so Docker can cache this layer
# separately from source code changes.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Runs the Vite dev server for now. A production build/Dockerfile
# stage can be added later when we deploy to the department server.
CMD ["npm", "run", "dev"]
