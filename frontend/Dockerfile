FROM node:20-alpine

WORKDIR /app

# Instalar dependências
COPY package.json package-lock.json* ./
RUN npm install

# Copiar resto do código
COPY . .

# Construir a aplicação
RUN npm run build

# Expor a porta
EXPOSE 3000

# Iniciar o Next.js
CMD ["npm", "run", "start"]
