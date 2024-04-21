FROM nginx:stable-alpine

COPY ./infra/api/nginx_usw.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]