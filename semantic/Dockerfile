# Cube semantic layer image: base Cube + the governed data model baked in.
# Single source of truth for the model is this directory (also used by
# docker-compose for local dev).
FROM cubejs/cube:latest

COPY cube.js /cube/conf/cube.js
COPY model /cube/conf/model
