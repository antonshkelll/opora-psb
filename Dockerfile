FROM python:3.11.14-slim
WORKDIR /app
COPY core.py server.py solution.py requirements.txt fetch_materials.py ./
COPY web ./web
COPY data ./data
RUN if [ ! -f data/knowledge-base.zip ]; then python fetch_materials.py; fi
RUN useradd --create-home app && chown -R app:app /app
USER app
EXPOSE 8080
CMD ["python", "server.py"]
