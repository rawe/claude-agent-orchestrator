FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Vite env vars must be available at build time
ARG VITE_AGENT_ORCHESTRATOR_API_URL
ARG VITE_DOCUMENT_SERVER_URL
ARG VITE_AGENT_ORCHESTRATOR_API_KEY
ENV VITE_AGENT_ORCHESTRATOR_API_URL=$VITE_AGENT_ORCHESTRATOR_API_URL
ENV VITE_DOCUMENT_SERVER_URL=$VITE_DOCUMENT_SERVER_URL
ENV VITE_AGENT_ORCHESTRATOR_API_KEY=$VITE_AGENT_ORCHESTRATOR_API_KEY

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
