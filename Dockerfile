# Prism in a container: the window served on a fixed port, or the engine as a
# one-off command. Standard library only, so there is nothing to pip install.
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 prism
WORKDIR /app
COPY engine/ /app/engine/

ENV PYTHONUNBUFFERED=1 \
    PRISM_HOST=0.0.0.0 \
    PRISM_PORT=8196 \
    PRISM_WORK=/work

USER prism
VOLUME /work
EXPOSE 8196

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD python3 -c "import socket,os; socket.create_connection(('127.0.0.1', int(os.environ['PRISM_PORT'])), 3)"

# docker compose run --rm prism engine/optimise3mf.py --list   for the engine
ENTRYPOINT ["python3"]
CMD ["engine/gui.py"]
