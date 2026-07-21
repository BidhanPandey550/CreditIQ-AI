FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Dev server for the MVP. Production builds static assets and serves them via Nginx.
CMD ["npm", "run", "dev"]
