FROM python:3.12-slim
WORKDIR /app
COPY *.py ./
COPY web ./web
COPY catalogo ./catalogo
RUN useradd --create-home yapu && mkdir /data && chown yapu /data
ENV YAPU_HOST=0.0.0.0 PORT=8765 YAPU_HTTPS=1 YAPU_DATA=/data
EXPOSE 8765
CMD ["python", "-u", "inicio_contenedor.py"]
