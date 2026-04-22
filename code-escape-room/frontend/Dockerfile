FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --platform=linux --arch=x64

COPY . .

CMD ["npm", "run", "dev", "--", "--host"]